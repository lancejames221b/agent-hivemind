"""
Claude Plugin Distribution System for hAIveMind

Enables distribution of Claude Code plugins across the hAIveMind collective.
Plugins bundle commands, agents, skills, hooks, and MCP servers.

Features:
- Plugin registry with semantic search
- Machine-group-based plugin distribution
- Version management with dependency resolution
- Sync across hAIveMind collective via sync_service
"""

import sqlite3
import json
import logging
import hashlib
import shutil
import os
import re
import zipfile
import base64
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from pathlib import Path
from enum import Enum
import yaml

logger = logging.getLogger(__name__)


class PluginStatus(Enum):
    """Plugin lifecycle status"""
    REGISTERED = "registered"      # Plugin registered but not published
    PUBLISHED = "published"        # Available for installation
    DEPRECATED = "deprecated"      # No longer recommended
    ARCHIVED = "archived"          # Removed from active use


class InstallationStatus(Enum):
    """Plugin installation status on a machine"""
    PENDING = "pending"            # Scheduled for installation
    INSTALLING = "installing"      # Installation in progress
    INSTALLED = "installed"        # Successfully installed
    FAILED = "failed"              # Installation failed
    UPDATING = "updating"          # Update in progress
    REMOVING = "removing"          # Removal in progress


class ComponentType(Enum):
    """Types of components in a plugin"""
    COMMAND = "command"
    AGENT = "agent"
    SKILL = "skill"
    HOOK = "hook"
    MCP_SERVER = "mcp_server"
    OTHER = "other"


@dataclass
class PluginManifest:
    """Parsed plugin.json manifest"""
    name: str
    version: str
    description: str = ""
    author_name: str = ""
    author_org: str = ""

    # hAIveMind-specific fields
    machine_groups: List[str] = field(default_factory=list)
    required_capabilities: List[str] = field(default_factory=list)
    min_haivemind_version: str = "1.0.0"

    # Component paths
    commands_path: Optional[str] = None
    agents_path: Optional[str] = None
    skills_path: Optional[str] = None
    hooks_path: Optional[str] = None
    mcp_servers_path: Optional[str] = None

    # Dependencies
    plugin_dependencies: Dict[str, str] = field(default_factory=dict)
    mcp_dependencies: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PluginManifest':
        """Parse manifest from dictionary"""
        haivemind = data.get('haivemind', {})
        components = data.get('components', {})
        dependencies = data.get('dependencies', {})
        author = data.get('author', {})

        return cls(
            name=data.get('name', ''),
            version=data.get('version', '0.0.0'),
            description=data.get('description', ''),
            author_name=author.get('name', '') if isinstance(author, dict) else str(author),
            author_org=author.get('organization', '') if isinstance(author, dict) else '',
            machine_groups=haivemind.get('machine_groups', []),
            required_capabilities=haivemind.get('required_capabilities', []),
            min_haivemind_version=haivemind.get('min_haivemind_version', '1.0.0'),
            commands_path=components.get('commands'),
            agents_path=components.get('agents'),
            skills_path=components.get('skills'),
            hooks_path=components.get('hooks'),
            mcp_servers_path=components.get('mcpServers'),
            plugin_dependencies=dependencies.get('plugins', {}),
            mcp_dependencies=dependencies.get('mcp_servers', [])
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'author': {
                'name': self.author_name,
                'organization': self.author_org
            },
            'haivemind': {
                'machine_groups': self.machine_groups,
                'required_capabilities': self.required_capabilities,
                'min_haivemind_version': self.min_haivemind_version
            },
            'components': {
                'commands': self.commands_path,
                'agents': self.agents_path,
                'skills': self.skills_path,
                'hooks': self.hooks_path,
                'mcpServers': self.mcp_servers_path
            },
            'dependencies': {
                'plugins': self.plugin_dependencies,
                'mcp_servers': self.mcp_dependencies
            }
        }


@dataclass
class Plugin:
    """Core plugin representation"""
    id: str
    name: str
    version: str
    description: str
    manifest: PluginManifest
    status: PluginStatus
    checksum: str
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None


@dataclass
class PluginFile:
    """Individual file within a plugin"""
    id: int
    plugin_id: str
    file_path: str
    file_type: ComponentType
    content: str
    checksum: str
    created_at: datetime


@dataclass
class PluginInstallation:
    """Plugin installation state on a machine"""
    id: int
    plugin_id: str
    machine_id: str
    installed_version: str
    status: InstallationStatus
    install_path: str
    installed_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None


class PluginSystem:
    """
    Claude Plugin Distribution System for hAIveMind

    Manages plugin registration, storage, distribution, and installation
    across the hAIveMind collective.
    """

    def __init__(self, db_path: str = "data/plugins.db", config: Dict[str, Any] = None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.config = config or {}

        # Default install path for plugins
        self.default_install_path = Path(
            self.config.get('install_path', os.path.expanduser('~/.claude/plugins'))
        )
        self.default_install_path.mkdir(parents=True, exist_ok=True)

        # Machine groups from config
        self.machine_groups = self.config.get('machine_groups', {})

        self._init_database()
        logger.info("🔌 Plugin System initialized")

    def _init_database(self):
        """Initialize SQLite database with plugin schema"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")

        try:
            # Core plugin registry
            conn.execute('''
                CREATE TABLE IF NOT EXISTS plugins (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    description TEXT,
                    author_name TEXT,
                    author_org TEXT,
                    manifest TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    status TEXT DEFAULT 'registered',
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name, version)
                )
            ''')

            # Plugin file storage
            conn.execute('''
                CREATE TABLE IF NOT EXISTS plugin_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plugin_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE,
                    UNIQUE(plugin_id, file_path)
                )
            ''')

            # Installation tracking per machine
            conn.execute('''
                CREATE TABLE IF NOT EXISTS plugin_installations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plugin_id TEXT NOT NULL,
                    machine_id TEXT NOT NULL,
                    installed_version TEXT NOT NULL,
                    status TEXT DEFAULT 'installed',
                    install_path TEXT,
                    installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    error_message TEXT,
                    FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE,
                    UNIQUE(plugin_id, machine_id)
                )
            ''')

            # Dependency tracking
            conn.execute('''
                CREATE TABLE IF NOT EXISTS plugin_dependencies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plugin_id TEXT NOT NULL,
                    depends_on_name TEXT NOT NULL,
                    depends_on_version TEXT NOT NULL,
                    dependency_type TEXT DEFAULT 'required',
                    FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE,
                    UNIQUE(plugin_id, depends_on_name)
                )
            ''')

            # Machine group compatibility
            conn.execute('''
                CREATE TABLE IF NOT EXISTS plugin_machine_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plugin_id TEXT NOT NULL,
                    machine_group TEXT NOT NULL,
                    FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE,
                    UNIQUE(plugin_id, machine_group)
                )
            ''')

            # Sync tracking for distributed updates
            conn.execute('''
                CREATE TABLE IF NOT EXISTS plugin_sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plugin_id TEXT NOT NULL,
                    machine_id TEXT NOT NULL,
                    sync_type TEXT NOT NULL,
                    sync_status TEXT NOT NULL,
                    sync_details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE
                )
            ''')

            # Indexes for performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_plugins_name ON plugins(name)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_plugins_status ON plugins(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_installations_machine ON plugin_installations(machine_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_installations_status ON plugin_installations(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_machine_groups_group ON plugin_machine_groups(machine_group)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_files_type ON plugin_files(file_type)')

            conn.commit()
        finally:
            conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _generate_plugin_id(self, name: str, version: str) -> str:
        """Generate unique plugin ID"""
        return f"plugin_{name}_{version}".replace('.', '_').replace('-', '_')

    def _calculate_checksum(self, content: str) -> str:
        """Calculate SHA256 checksum"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _detect_file_type(self, file_path: str) -> ComponentType:
        """Detect component type from file path"""
        path_lower = file_path.lower()

        if '/commands/' in path_lower or path_lower.endswith('.md') and 'command' in path_lower:
            return ComponentType.COMMAND
        elif '/agents/' in path_lower:
            return ComponentType.AGENT
        elif '/skills/' in path_lower or 'skill.md' in path_lower:
            return ComponentType.SKILL
        elif 'hooks.json' in path_lower or '/hooks/' in path_lower:
            return ComponentType.HOOK
        elif '.mcp.json' in path_lower or 'mcp' in path_lower:
            return ComponentType.MCP_SERVER
        else:
            return ComponentType.OTHER

    # ===================
    # Plugin Registration
    # ===================

    def register_plugin_from_directory(
        self,
        plugin_path: str,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a plugin from a local directory.

        Args:
            plugin_path: Path to plugin directory containing .claude-plugin/plugin.json
            created_by: Agent/user ID registering the plugin

        Returns:
            Dict with plugin_id and registration status
        """
        plugin_dir = Path(plugin_path)

        # Find and parse manifest
        manifest_path = plugin_dir / '.claude-plugin' / 'plugin.json'
        if not manifest_path.exists():
            # Try alternate location
            manifest_path = plugin_dir / 'plugin.json'

        if not manifest_path.exists():
            return {
                'success': False,
                'error': f"No plugin.json found in {plugin_path}"
            }

        try:
            with open(manifest_path, 'r') as f:
                manifest_data = json.load(f)
        except json.JSONDecodeError as e:
            return {
                'success': False,
                'error': f"Invalid plugin.json: {e}"
            }

        manifest = PluginManifest.from_dict(manifest_data)

        if not manifest.name or not manifest.version:
            return {
                'success': False,
                'error': "Plugin manifest must have name and version"
            }

        # Collect all plugin files
        files: Dict[str, Tuple[str, ComponentType]] = {}

        for root, dirs, filenames in os.walk(plugin_dir):
            # Skip hidden directories except .claude-plugin
            dirs[:] = [d for d in dirs if not d.startswith('.') or d == '.claude-plugin']

            for filename in filenames:
                file_path = Path(root) / filename
                rel_path = file_path.relative_to(plugin_dir)

                # Skip certain files
                if filename.startswith('.') and filename not in ['.mcp.json']:
                    continue
                if filename.endswith('.pyc') or '__pycache__' in str(rel_path):
                    continue

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    file_type = self._detect_file_type(str(rel_path))
                    files[str(rel_path)] = (content, file_type)
                except (UnicodeDecodeError, IOError):
                    # Skip binary files
                    continue

        return self._register_plugin(manifest, files, created_by)

    def register_plugin_from_archive(
        self,
        archive_base64: str,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a plugin from a base64-encoded zip archive.

        Args:
            archive_base64: Base64-encoded zip file
            created_by: Agent/user ID registering the plugin

        Returns:
            Dict with plugin_id and registration status
        """
        try:
            archive_bytes = base64.b64decode(archive_base64)
        except Exception as e:
            return {
                'success': False,
                'error': f"Invalid base64 archive: {e}"
            }

        with tempfile.TemporaryDirectory() as tmpdir:
            archive_path = Path(tmpdir) / 'plugin.zip'
            extract_path = Path(tmpdir) / 'plugin'

            with open(archive_path, 'wb') as f:
                f.write(archive_bytes)

            try:
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    zf.extractall(extract_path)
            except zipfile.BadZipFile as e:
                return {
                    'success': False,
                    'error': f"Invalid zip archive: {e}"
                }

            # Find the plugin root (might be nested in a folder)
            plugin_root = extract_path
            entries = list(extract_path.iterdir())
            if len(entries) == 1 and entries[0].is_dir():
                plugin_root = entries[0]

            return self.register_plugin_from_directory(str(plugin_root), created_by)

    def _register_plugin(
        self,
        manifest: PluginManifest,
        files: Dict[str, Tuple[str, ComponentType]],
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """Internal method to register a plugin with parsed manifest and files"""

        plugin_id = self._generate_plugin_id(manifest.name, manifest.version)

        # Calculate overall checksum from all files
        all_content = ''.join(content for content, _ in files.values())
        checksum = self._calculate_checksum(all_content + json.dumps(manifest.to_dict()))

        conn = self._get_connection()
        try:
            # Check if already exists
            existing = conn.execute(
                'SELECT id FROM plugins WHERE name = ? AND version = ?',
                (manifest.name, manifest.version)
            ).fetchone()

            if existing:
                return {
                    'success': False,
                    'error': f"Plugin {manifest.name}@{manifest.version} already registered",
                    'plugin_id': existing['id']
                }

            # Insert plugin
            conn.execute('''
                INSERT INTO plugins (id, name, version, description, author_name, author_org,
                                   manifest, checksum, status, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                plugin_id,
                manifest.name,
                manifest.version,
                manifest.description,
                manifest.author_name,
                manifest.author_org,
                json.dumps(manifest.to_dict()),
                checksum,
                PluginStatus.REGISTERED.value,
                created_by
            ))

            # Insert files
            for file_path, (content, file_type) in files.items():
                file_checksum = self._calculate_checksum(content)
                conn.execute('''
                    INSERT INTO plugin_files (plugin_id, file_path, file_type, content, checksum)
                    VALUES (?, ?, ?, ?, ?)
                ''', (plugin_id, file_path, file_type.value, content, file_checksum))

            # Insert machine groups
            for group in manifest.machine_groups:
                conn.execute('''
                    INSERT INTO plugin_machine_groups (plugin_id, machine_group)
                    VALUES (?, ?)
                ''', (plugin_id, group))

            # Insert dependencies
            for dep_name, dep_version in manifest.plugin_dependencies.items():
                conn.execute('''
                    INSERT INTO plugin_dependencies (plugin_id, depends_on_name, depends_on_version)
                    VALUES (?, ?, ?)
                ''', (plugin_id, dep_name, dep_version))

            conn.commit()

            logger.info(f"✅ Registered plugin: {manifest.name}@{manifest.version}")

            return {
                'success': True,
                'plugin_id': plugin_id,
                'name': manifest.name,
                'version': manifest.version,
                'files_count': len(files),
                'components': {
                    'commands': sum(1 for _, (_, t) in files.items() if t == ComponentType.COMMAND),
                    'agents': sum(1 for _, (_, t) in files.items() if t == ComponentType.AGENT),
                    'skills': sum(1 for _, (_, t) in files.items() if t == ComponentType.SKILL),
                    'hooks': sum(1 for _, (_, t) in files.items() if t == ComponentType.HOOK),
                    'mcp_servers': sum(1 for _, (_, t) in files.items() if t == ComponentType.MCP_SERVER),
                }
            }

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to register plugin: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            conn.close()

    # =================
    # Plugin Publishing
    # =================

    def publish_plugin(
        self,
        plugin_id: str,
        target_groups: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Publish a registered plugin to make it available for installation.

        Args:
            plugin_id: Plugin ID to publish
            target_groups: Optional list of machine groups (overrides manifest)

        Returns:
            Dict with publication status
        """
        conn = self._get_connection()
        try:
            # Get plugin
            plugin_row = conn.execute(
                'SELECT * FROM plugins WHERE id = ?',
                (plugin_id,)
            ).fetchone()

            if not plugin_row:
                return {
                    'success': False,
                    'error': f"Plugin not found: {plugin_id}"
                }

            if plugin_row['status'] == PluginStatus.PUBLISHED.value:
                return {
                    'success': True,
                    'message': 'Plugin already published',
                    'plugin_id': plugin_id
                }

            # Update status
            conn.execute('''
                UPDATE plugins SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (PluginStatus.PUBLISHED.value, plugin_id))

            # Update machine groups if specified
            if target_groups:
                conn.execute('DELETE FROM plugin_machine_groups WHERE plugin_id = ?', (plugin_id,))
                for group in target_groups:
                    conn.execute('''
                        INSERT INTO plugin_machine_groups (plugin_id, machine_group)
                        VALUES (?, ?)
                    ''', (plugin_id, group))

            conn.commit()

            logger.info(f"📢 Published plugin: {plugin_row['name']}@{plugin_row['version']}")

            return {
                'success': True,
                'plugin_id': plugin_id,
                'name': plugin_row['name'],
                'version': plugin_row['version'],
                'status': 'published'
            }

        finally:
            conn.close()

    # ==================
    # Plugin Listing
    # ==================

    def list_plugins(
        self,
        status_filter: Optional[str] = None,
        machine_group: Optional[str] = None,
        installed_only: bool = False,
        machine_id: Optional[str] = None,
        search_query: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List available plugins with filtering.

        Args:
            status_filter: Filter by status (registered, published, deprecated)
            machine_group: Filter by machine group compatibility
            installed_only: Only show installed plugins
            machine_id: Machine ID for installation status
            search_query: Search in name/description
            limit: Max results
            offset: Pagination offset

        Returns:
            Dict with plugins list and metadata
        """
        conn = self._get_connection()
        try:
            query = '''
                SELECT DISTINCT p.*,
                       (SELECT GROUP_CONCAT(machine_group) FROM plugin_machine_groups WHERE plugin_id = p.id) as machine_groups
                FROM plugins p
            '''
            params = []
            conditions = []

            if status_filter:
                conditions.append('p.status = ?')
                params.append(status_filter)

            if machine_group:
                query += ' JOIN plugin_machine_groups pmg ON p.id = pmg.plugin_id'
                conditions.append('pmg.machine_group = ?')
                params.append(machine_group)

            if installed_only and machine_id:
                query += ' JOIN plugin_installations pi ON p.id = pi.plugin_id'
                conditions.append("pi.machine_id = ? AND pi.status = 'installed'")
                params.append(machine_id)

            if search_query:
                conditions.append('(p.name LIKE ? OR p.description LIKE ?)')
                params.extend([f'%{search_query}%', f'%{search_query}%'])

            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)

            query += ' ORDER BY p.updated_at DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])

            rows = conn.execute(query, params).fetchall()

            plugins = []
            for row in rows:
                # Get installation status if machine_id provided
                install_status = None
                if machine_id:
                    install_row = conn.execute('''
                        SELECT status, installed_version FROM plugin_installations
                        WHERE plugin_id = ? AND machine_id = ?
                    ''', (row['id'], machine_id)).fetchone()
                    if install_row:
                        install_status = {
                            'status': install_row['status'],
                            'version': install_row['installed_version']
                        }

                plugins.append({
                    'id': row['id'],
                    'name': row['name'],
                    'version': row['version'],
                    'description': row['description'],
                    'author': row['author_name'],
                    'status': row['status'],
                    'machine_groups': row['machine_groups'].split(',') if row['machine_groups'] else [],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'installation': install_status
                })

            # Get total count
            count_query = 'SELECT COUNT(DISTINCT p.id) FROM plugins p'
            if machine_group:
                count_query += ' JOIN plugin_machine_groups pmg ON p.id = pmg.plugin_id'
            count_conditions = [c for c in conditions if 'pi.' not in c][:2]  # Only basic filters
            if count_conditions:
                count_query += ' WHERE ' + ' AND '.join(count_conditions)

            count_params = params[:len(count_conditions)]
            total = conn.execute(count_query, count_params).fetchone()[0]

            return {
                'success': True,
                'plugins': plugins,
                'total': total,
                'limit': limit,
                'offset': offset
            }

        finally:
            conn.close()

    def get_plugin(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed plugin information"""
        conn = self._get_connection()
        try:
            row = conn.execute('SELECT * FROM plugins WHERE id = ?', (plugin_id,)).fetchone()

            if not row:
                return None

            # Get files
            files = conn.execute(
                'SELECT file_path, file_type FROM plugin_files WHERE plugin_id = ?',
                (plugin_id,)
            ).fetchall()

            # Get machine groups
            groups = conn.execute(
                'SELECT machine_group FROM plugin_machine_groups WHERE plugin_id = ?',
                (plugin_id,)
            ).fetchall()

            # Get dependencies
            deps = conn.execute(
                'SELECT depends_on_name, depends_on_version FROM plugin_dependencies WHERE plugin_id = ?',
                (plugin_id,)
            ).fetchall()

            # Get installations
            installations = conn.execute(
                'SELECT machine_id, installed_version, status, installed_at FROM plugin_installations WHERE plugin_id = ?',
                (plugin_id,)
            ).fetchall()

            return {
                'id': row['id'],
                'name': row['name'],
                'version': row['version'],
                'description': row['description'],
                'author_name': row['author_name'],
                'author_org': row['author_org'],
                'manifest': json.loads(row['manifest']),
                'checksum': row['checksum'],
                'status': row['status'],
                'created_by': row['created_by'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
                'files': [{'path': f['file_path'], 'type': f['file_type']} for f in files],
                'machine_groups': [g['machine_group'] for g in groups],
                'dependencies': {d['depends_on_name']: d['depends_on_version'] for d in deps},
                'installations': [
                    {
                        'machine_id': i['machine_id'],
                        'version': i['installed_version'],
                        'status': i['status'],
                        'installed_at': i['installed_at']
                    }
                    for i in installations
                ]
            }

        finally:
            conn.close()

    # ====================
    # Plugin Installation
    # ====================

    def install_plugin(
        self,
        plugin_id: str,
        machine_id: str,
        install_path: Optional[str] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Install a plugin on the local machine.

        Args:
            plugin_id: Plugin ID to install
            machine_id: Target machine ID
            install_path: Custom installation path (default: ~/.claude/plugins)
            force: Force reinstall if already installed

        Returns:
            Dict with installation status
        """
        conn = self._get_connection()
        try:
            # Get plugin
            plugin = self.get_plugin(plugin_id)
            if not plugin:
                return {
                    'success': False,
                    'error': f"Plugin not found: {plugin_id}"
                }

            if plugin['status'] != PluginStatus.PUBLISHED.value:
                return {
                    'success': False,
                    'error': f"Plugin not published: {plugin_id}"
                }

            # Check if already installed
            existing = conn.execute('''
                SELECT * FROM plugin_installations
                WHERE plugin_id = ? AND machine_id = ?
            ''', (plugin_id, machine_id)).fetchone()

            if existing and not force:
                if existing['status'] == InstallationStatus.INSTALLED.value:
                    return {
                        'success': False,
                        'error': f"Plugin already installed. Use force=True to reinstall.",
                        'installed_version': existing['installed_version']
                    }

            # Resolve install path
            base_path = Path(install_path) if install_path else self.default_install_path
            plugin_install_dir = base_path / plugin['name']

            # Update status to installing
            if existing:
                conn.execute('''
                    UPDATE plugin_installations
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE plugin_id = ? AND machine_id = ?
                ''', (InstallationStatus.INSTALLING.value, plugin_id, machine_id))
            else:
                conn.execute('''
                    INSERT INTO plugin_installations (plugin_id, machine_id, installed_version, status, install_path)
                    VALUES (?, ?, ?, ?, ?)
                ''', (plugin_id, machine_id, plugin['version'], InstallationStatus.INSTALLING.value, str(plugin_install_dir)))

            conn.commit()

            try:
                # Remove existing installation
                if plugin_install_dir.exists():
                    shutil.rmtree(plugin_install_dir)

                # Get plugin files
                files = conn.execute(
                    'SELECT file_path, file_type, content FROM plugin_files WHERE plugin_id = ?',
                    (plugin_id,)
                ).fetchall()

                # Install files
                installed_components = {
                    'commands': [],
                    'agents': [],
                    'skills': [],
                    'hooks': [],
                    'mcp_servers': []
                }

                for file_row in files:
                    file_path = plugin_install_dir / file_row['file_path']
                    file_path.parent.mkdir(parents=True, exist_ok=True)

                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(file_row['content'])

                    # Track by component type
                    file_type = file_row['file_type']
                    if file_type == ComponentType.COMMAND.value:
                        installed_components['commands'].append(file_row['file_path'])
                    elif file_type == ComponentType.AGENT.value:
                        installed_components['agents'].append(file_row['file_path'])
                    elif file_type == ComponentType.SKILL.value:
                        installed_components['skills'].append(file_row['file_path'])
                    elif file_type == ComponentType.HOOK.value:
                        installed_components['hooks'].append(file_row['file_path'])
                    elif file_type == ComponentType.MCP_SERVER.value:
                        installed_components['mcp_servers'].append(file_row['file_path'])

                # Create symlinks to Claude Code directories
                self._create_claude_symlinks(plugin_install_dir, plugin['name'], installed_components)

                # Update status to installed
                conn.execute('''
                    UPDATE plugin_installations
                    SET status = ?, installed_version = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE plugin_id = ? AND machine_id = ?
                ''', (InstallationStatus.INSTALLED.value, plugin['version'], plugin_id, machine_id))

                # Log sync event
                conn.execute('''
                    INSERT INTO plugin_sync_log (plugin_id, machine_id, sync_type, sync_status, sync_details)
                    VALUES (?, ?, 'install', 'success', ?)
                ''', (plugin_id, machine_id, json.dumps(installed_components)))

                conn.commit()

                logger.info(f"✅ Installed plugin {plugin['name']}@{plugin['version']} to {plugin_install_dir}")

                return {
                    'success': True,
                    'plugin_id': plugin_id,
                    'name': plugin['name'],
                    'version': plugin['version'],
                    'install_path': str(plugin_install_dir),
                    'components': installed_components
                }

            except Exception as e:
                # Update status to failed
                conn.execute('''
                    UPDATE plugin_installations
                    SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE plugin_id = ? AND machine_id = ?
                ''', (InstallationStatus.FAILED.value, str(e), plugin_id, machine_id))
                conn.commit()

                logger.error(f"Failed to install plugin {plugin_id}: {e}")
                return {
                    'success': False,
                    'error': str(e)
                }

        finally:
            conn.close()

    def _create_claude_symlinks(
        self,
        plugin_dir: Path,
        plugin_name: str,
        components: Dict[str, List[str]]
    ):
        """Create symlinks from plugin directory to Claude Code directories"""

        claude_dir = Path.home() / '.claude'

        # Commands -> .claude/commands/
        if components.get('commands'):
            commands_dir = claude_dir / 'commands'
            commands_dir.mkdir(parents=True, exist_ok=True)

            for cmd_path in components['commands']:
                src = plugin_dir / cmd_path
                if src.exists():
                    dst = commands_dir / f"{plugin_name}_{src.name}"
                    if dst.exists() or dst.is_symlink():
                        dst.unlink()
                    dst.symlink_to(src)

        # Agents -> .claude/agents/
        if components.get('agents'):
            agents_dir = claude_dir / 'agents'
            agents_dir.mkdir(parents=True, exist_ok=True)

            for agent_path in components['agents']:
                src = plugin_dir / agent_path
                if src.exists():
                    dst = agents_dir / f"{plugin_name}_{src.name}"
                    if dst.exists() or dst.is_symlink():
                        dst.unlink()
                    dst.symlink_to(src)

        # Skills -> .claude/skills/
        if components.get('skills'):
            skills_dir = claude_dir / 'skills'
            skills_dir.mkdir(parents=True, exist_ok=True)

            for skill_path in components['skills']:
                src = plugin_dir / skill_path
                if src.is_dir():
                    dst = skills_dir / f"{plugin_name}_{src.name}"
                    if dst.exists() or dst.is_symlink():
                        if dst.is_symlink():
                            dst.unlink()
                        else:
                            shutil.rmtree(dst)
                    dst.symlink_to(src)
                elif src.exists():
                    # Single SKILL.md file - create containing directory
                    skill_name = src.parent.name if src.name.lower() == 'skill.md' else src.stem
                    dst_dir = skills_dir / f"{plugin_name}_{skill_name}"
                    dst_dir.mkdir(parents=True, exist_ok=True)
                    dst = dst_dir / 'SKILL.md'
                    if dst.exists() or dst.is_symlink():
                        dst.unlink()
                    dst.symlink_to(src)

    def uninstall_plugin(
        self,
        plugin_id: str,
        machine_id: str,
        keep_data: bool = False
    ) -> Dict[str, Any]:
        """
        Uninstall a plugin from the local machine.

        Args:
            plugin_id: Plugin ID to uninstall
            machine_id: Machine ID
            keep_data: Keep plugin data files

        Returns:
            Dict with uninstallation status
        """
        conn = self._get_connection()
        try:
            # Get installation info
            install_row = conn.execute('''
                SELECT * FROM plugin_installations
                WHERE plugin_id = ? AND machine_id = ?
            ''', (plugin_id, machine_id)).fetchone()

            if not install_row:
                return {
                    'success': False,
                    'error': f"Plugin not installed on this machine"
                }

            # Get plugin info
            plugin = self.get_plugin(plugin_id)
            if not plugin:
                return {
                    'success': False,
                    'error': f"Plugin not found: {plugin_id}"
                }

            # Update status
            conn.execute('''
                UPDATE plugin_installations
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE plugin_id = ? AND machine_id = ?
            ''', (InstallationStatus.REMOVING.value, plugin_id, machine_id))
            conn.commit()

            try:
                install_path = Path(install_row['install_path'])

                # Remove symlinks first
                self._remove_claude_symlinks(plugin['name'])

                # Remove plugin directory
                if not keep_data and install_path.exists():
                    shutil.rmtree(install_path)

                # Remove installation record
                conn.execute('''
                    DELETE FROM plugin_installations
                    WHERE plugin_id = ? AND machine_id = ?
                ''', (plugin_id, machine_id))

                # Log sync event
                conn.execute('''
                    INSERT INTO plugin_sync_log (plugin_id, machine_id, sync_type, sync_status, sync_details)
                    VALUES (?, ?, 'uninstall', 'success', ?)
                ''', (plugin_id, machine_id, json.dumps({'keep_data': keep_data})))

                conn.commit()

                logger.info(f"🗑️ Uninstalled plugin {plugin['name']} from {machine_id}")

                return {
                    'success': True,
                    'plugin_id': plugin_id,
                    'name': plugin['name'],
                    'machine_id': machine_id
                }

            except Exception as e:
                conn.execute('''
                    UPDATE plugin_installations
                    SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE plugin_id = ? AND machine_id = ?
                ''', (InstallationStatus.FAILED.value, str(e), plugin_id, machine_id))
                conn.commit()

                return {
                    'success': False,
                    'error': str(e)
                }

        finally:
            conn.close()

    def _remove_claude_symlinks(self, plugin_name: str):
        """Remove symlinks for a plugin from Claude Code directories"""
        claude_dir = Path.home() / '.claude'

        for subdir in ['commands', 'agents', 'skills']:
            target_dir = claude_dir / subdir
            if target_dir.exists():
                for item in target_dir.iterdir():
                    if item.is_symlink() and item.name.startswith(f"{plugin_name}_"):
                        item.unlink()

    # ================
    # Plugin Sync
    # ================

    def get_sync_payload(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """
        Get plugin data for syncing to other machines.

        Returns complete plugin data including all files.
        """
        conn = self._get_connection()
        try:
            plugin = self.get_plugin(plugin_id)
            if not plugin:
                return None

            # Get full file contents
            files = conn.execute(
                'SELECT file_path, file_type, content, checksum FROM plugin_files WHERE plugin_id = ?',
                (plugin_id,)
            ).fetchall()

            return {
                'id': plugin['id'],
                'name': plugin['name'],
                'version': plugin['version'],
                'description': plugin['description'],
                'manifest': plugin['manifest'],
                'checksum': plugin['checksum'],
                'status': plugin['status'],
                'machine_groups': plugin['machine_groups'],
                'dependencies': plugin['dependencies'],
                'files': [
                    {
                        'path': f['file_path'],
                        'type': f['file_type'],
                        'content': f['content'],
                        'checksum': f['checksum']
                    }
                    for f in files
                ]
            }

        finally:
            conn.close()

    def import_plugin_from_sync(self, sync_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Import a plugin from sync payload (received from another machine).

        Args:
            sync_payload: Plugin data from get_sync_payload()

        Returns:
            Dict with import status
        """
        conn = self._get_connection()
        try:
            plugin_id = sync_payload['id']

            # Check if already exists
            existing = conn.execute(
                'SELECT id, checksum FROM plugins WHERE id = ?',
                (plugin_id,)
            ).fetchone()

            if existing:
                if existing['checksum'] == sync_payload['checksum']:
                    return {
                        'success': True,
                        'message': 'Plugin already up to date',
                        'plugin_id': plugin_id
                    }
                # Update existing
                conn.execute('DELETE FROM plugins WHERE id = ?', (plugin_id,))

            # Parse manifest
            manifest = PluginManifest.from_dict(sync_payload['manifest'])

            # Insert plugin
            conn.execute('''
                INSERT INTO plugins (id, name, version, description, author_name, author_org,
                                   manifest, checksum, status, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                plugin_id,
                sync_payload['name'],
                sync_payload['version'],
                sync_payload['description'],
                manifest.author_name,
                manifest.author_org,
                json.dumps(sync_payload['manifest']),
                sync_payload['checksum'],
                sync_payload['status'],
                'sync'
            ))

            # Insert files
            for file_data in sync_payload['files']:
                conn.execute('''
                    INSERT INTO plugin_files (plugin_id, file_path, file_type, content, checksum)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    plugin_id,
                    file_data['path'],
                    file_data['type'],
                    file_data['content'],
                    file_data['checksum']
                ))

            # Insert machine groups
            for group in sync_payload.get('machine_groups', []):
                conn.execute('''
                    INSERT OR IGNORE INTO plugin_machine_groups (plugin_id, machine_group)
                    VALUES (?, ?)
                ''', (plugin_id, group))

            # Insert dependencies
            for dep_name, dep_version in sync_payload.get('dependencies', {}).items():
                conn.execute('''
                    INSERT OR IGNORE INTO plugin_dependencies (plugin_id, depends_on_name, depends_on_version)
                    VALUES (?, ?, ?)
                ''', (plugin_id, dep_name, dep_version))

            conn.commit()

            logger.info(f"📥 Imported plugin from sync: {sync_payload['name']}@{sync_payload['version']}")

            return {
                'success': True,
                'plugin_id': plugin_id,
                'name': sync_payload['name'],
                'version': sync_payload['version']
            }

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to import plugin from sync: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            conn.close()

    def get_plugins_for_machine_group(self, machine_group: str) -> List[Dict[str, Any]]:
        """Get all published plugins compatible with a machine group"""
        result = self.list_plugins(
            status_filter=PluginStatus.PUBLISHED.value,
            machine_group=machine_group
        )
        return result.get('plugins', [])

    def get_installation_status(self, machine_id: str) -> Dict[str, Any]:
        """Get all plugin installations for a machine"""
        conn = self._get_connection()
        try:
            rows = conn.execute('''
                SELECT pi.*, p.name, p.version as latest_version
                FROM plugin_installations pi
                JOIN plugins p ON pi.plugin_id = p.id
                WHERE pi.machine_id = ?
            ''', (machine_id,)).fetchall()

            installations = []
            updates_available = []

            for row in rows:
                installation = {
                    'plugin_id': row['plugin_id'],
                    'name': row['name'],
                    'installed_version': row['installed_version'],
                    'latest_version': row['latest_version'],
                    'status': row['status'],
                    'install_path': row['install_path'],
                    'installed_at': row['installed_at'],
                    'updated_at': row['updated_at']
                }
                installations.append(installation)

                if row['installed_version'] != row['latest_version']:
                    updates_available.append({
                        'name': row['name'],
                        'current': row['installed_version'],
                        'available': row['latest_version']
                    })

            return {
                'machine_id': machine_id,
                'installed_count': len(installations),
                'installations': installations,
                'updates_available': updates_available
            }

        finally:
            conn.close()

    # ====================
    # Plugin Statistics
    # ====================

    def get_stats(self) -> Dict[str, Any]:
        """Get plugin system statistics"""
        conn = self._get_connection()
        try:
            stats = {}

            # Plugin counts by status
            rows = conn.execute('''
                SELECT status, COUNT(*) as count FROM plugins GROUP BY status
            ''').fetchall()
            stats['plugins_by_status'] = {row['status']: row['count'] for row in rows}
            stats['total_plugins'] = sum(stats['plugins_by_status'].values())

            # Installation counts
            rows = conn.execute('''
                SELECT status, COUNT(*) as count FROM plugin_installations GROUP BY status
            ''').fetchall()
            stats['installations_by_status'] = {row['status']: row['count'] for row in rows}
            stats['total_installations'] = sum(stats['installations_by_status'].values())

            # Component counts
            rows = conn.execute('''
                SELECT file_type, COUNT(*) as count FROM plugin_files GROUP BY file_type
            ''').fetchall()
            stats['components_by_type'] = {row['file_type']: row['count'] for row in rows}

            # Machines with installations
            row = conn.execute('''
                SELECT COUNT(DISTINCT machine_id) as count FROM plugin_installations
            ''').fetchone()
            stats['machines_with_plugins'] = row['count']

            # Recent activity
            rows = conn.execute('''
                SELECT sync_type, COUNT(*) as count
                FROM plugin_sync_log
                WHERE created_at > datetime('now', '-24 hours')
                GROUP BY sync_type
            ''').fetchall()
            stats['recent_activity'] = {row['sync_type']: row['count'] for row in rows}

            return stats

        finally:
            conn.close()


# Convenience function for creating the system with config
def create_plugin_system(config_path: str = "config/config.json") -> PluginSystem:
    """Create a PluginSystem instance with config from file"""
    config = {}
    config_file = Path(config_path)

    if config_file.exists():
        with open(config_file) as f:
            full_config = json.load(f)
            config = full_config.get('plugins', {})
            config['machine_groups'] = full_config.get('memory', {}).get('machine_groups', {})

    db_path = config.get('registry_db', 'data/plugins.db')
    return PluginSystem(db_path=db_path, config=config)
