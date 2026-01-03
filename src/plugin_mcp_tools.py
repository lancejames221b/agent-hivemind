"""
Plugin MCP Tools for hAIveMind

Provides MCP tools for managing Claude Code plugins across the hAIveMind collective.
Integrates with the PluginSystem for registration, distribution, and installation.
"""

import json
import logging
import os
import socket
from typing import Any, Dict, List, Optional
from pathlib import Path

from plugin_system import PluginSystem, PluginStatus, InstallationStatus, create_plugin_system

logger = logging.getLogger(__name__)


class PluginMCPTools:
    """
    MCP Tools for Claude Plugin Management

    Provides tools for:
    - Registering plugins from directories or archives
    - Publishing plugins to the collective
    - Installing/uninstalling plugins on machines
    - Syncing plugins across the hAIveMind network
    - Querying plugin status and updates
    """

    def __init__(self, mcp_server, storage, config: Dict[str, Any]):
        """
        Initialize plugin MCP tools.

        Args:
            mcp_server: FastMCP server instance
            storage: MemoryStorage instance for hAIveMind integration
            config: Full configuration dict
        """
        self.mcp = mcp_server
        self.storage = storage
        self.config = config
        self.machine_id = self._get_machine_id()

        # Initialize plugin system
        plugin_config = config.get('plugins', {})
        plugin_config['machine_groups'] = config.get('memory', {}).get('machine_groups', {})
        db_path = plugin_config.get('registry_db', 'data/plugins.db')
        self.plugin_system = PluginSystem(db_path=db_path, config=plugin_config)

        # Register tools
        self._register_tools()

        logger.info("🔌 Plugin MCP Tools initialized")

    def _get_machine_id(self) -> str:
        """Get machine identifier"""
        try:
            import subprocess
            result = subprocess.run(['tailscale', 'status', '--json'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                status = json.loads(result.stdout)
                return status.get('Self', {}).get('HostName', socket.gethostname())
        except Exception:
            pass
        return socket.gethostname()

    def _register_tools(self):
        """Register all plugin management MCP tools"""

        # =====================
        # Plugin Registration
        # =====================

        @self.mcp.tool()
        async def register_plugin(
            plugin_path: str = None,
            plugin_archive: str = None
        ) -> str:
            """
            Register a new plugin with the hAIveMind collective.

            Provide either a local directory path or a base64-encoded zip archive.
            The plugin must contain a .claude-plugin/plugin.json manifest.

            Args:
                plugin_path: Local path to plugin directory
                plugin_archive: Base64-encoded zip archive of plugin

            Returns:
                JSON with registration status and plugin details

            Example:
                register_plugin plugin_path="/path/to/my-plugin"
            """
            if not plugin_path and not plugin_archive:
                return json.dumps({
                    'success': False,
                    'error': 'Provide either plugin_path or plugin_archive'
                })

            agent_id = getattr(self.storage, 'agent_id', self.machine_id)

            if plugin_path:
                result = self.plugin_system.register_plugin_from_directory(
                    plugin_path=plugin_path,
                    created_by=agent_id
                )
            else:
                result = self.plugin_system.register_plugin_from_archive(
                    archive_base64=plugin_archive,
                    created_by=agent_id
                )

            # Store registration event in hAIveMind memory
            if result.get('success'):
                try:
                    self.storage.store(
                        content=f"Registered plugin: {result.get('name')}@{result.get('version')}",
                        category='plugins',
                        context=json.dumps({
                            'action': 'register',
                            'plugin_id': result.get('plugin_id'),
                            'components': result.get('components', {})
                        }),
                        tags=['plugin', 'register', result.get('name', '')]
                    )
                except Exception as e:
                    logger.warning(f"Failed to store plugin registration in memory: {e}")

            return json.dumps(result, indent=2)

        @self.mcp.tool()
        async def publish_plugin(
            plugin_id: str,
            target_groups: str = None
        ) -> str:
            """
            Publish a registered plugin to make it available for installation.

            Args:
                plugin_id: Plugin ID to publish (e.g., plugin_my-plugin_1_0_0)
                target_groups: Comma-separated machine groups (optional, overrides manifest)

            Returns:
                JSON with publication status

            Example:
                publish_plugin plugin_id="plugin_devops-tools_1_0_0"
                publish_plugin plugin_id="plugin_es-ops_1_0_0" target_groups="elasticsearch,orchestrators"
            """
            groups = None
            if target_groups:
                groups = [g.strip() for g in target_groups.split(',')]

            result = self.plugin_system.publish_plugin(
                plugin_id=plugin_id,
                target_groups=groups
            )

            # Broadcast to hAIveMind if successful
            if result.get('success'):
                try:
                    self.storage.broadcast_discovery(
                        message=f"New plugin published: {result.get('name')}@{result.get('version')}",
                        category='plugins',
                        severity='info'
                    )
                except Exception as e:
                    logger.warning(f"Failed to broadcast plugin publication: {e}")

            return json.dumps(result, indent=2)

        # =====================
        # Plugin Installation
        # =====================

        @self.mcp.tool()
        async def install_plugin(
            plugin_id: str,
            install_path: str = None,
            force: bool = False
        ) -> str:
            """
            Install a published plugin on this machine.

            Creates symlinks to Claude Code directories (.claude/commands, .claude/agents, etc.)

            Args:
                plugin_id: Plugin ID to install
                install_path: Custom installation path (default: ~/.claude/plugins)
                force: Force reinstall if already installed

            Returns:
                JSON with installation status and installed components

            Example:
                install_plugin plugin_id="plugin_devops-tools_1_0_0"
                install_plugin plugin_id="plugin_devops-tools_1_0_0" force=true
            """
            result = self.plugin_system.install_plugin(
                plugin_id=plugin_id,
                machine_id=self.machine_id,
                install_path=install_path,
                force=force
            )

            # Log installation in hAIveMind memory
            if result.get('success'):
                try:
                    self.storage.store(
                        content=f"Installed plugin: {result.get('name')}@{result.get('version')} on {self.machine_id}",
                        category='plugins',
                        context=json.dumps({
                            'action': 'install',
                            'plugin_id': plugin_id,
                            'machine_id': self.machine_id,
                            'components': result.get('components', {})
                        }),
                        tags=['plugin', 'install', result.get('name', ''), self.machine_id]
                    )
                except Exception as e:
                    logger.warning(f"Failed to store plugin installation in memory: {e}")

            return json.dumps(result, indent=2)

        @self.mcp.tool()
        async def uninstall_plugin(
            plugin_id: str,
            keep_data: bool = False
        ) -> str:
            """
            Uninstall a plugin from this machine.

            Removes plugin files and Claude Code symlinks.

            Args:
                plugin_id: Plugin ID to uninstall
                keep_data: Keep plugin data files (default: False)

            Returns:
                JSON with uninstallation status

            Example:
                uninstall_plugin plugin_id="plugin_devops-tools_1_0_0"
            """
            result = self.plugin_system.uninstall_plugin(
                plugin_id=plugin_id,
                machine_id=self.machine_id,
                keep_data=keep_data
            )

            return json.dumps(result, indent=2)

        # =====================
        # Plugin Discovery
        # =====================

        @self.mcp.tool()
        async def list_plugins(
            status_filter: str = None,
            machine_group: str = None,
            installed_only: bool = False,
            search_query: str = None,
            limit: int = 50
        ) -> str:
            """
            List available plugins with filtering options.

            Args:
                status_filter: Filter by status (registered, published, deprecated)
                machine_group: Filter by compatible machine group
                installed_only: Only show plugins installed on this machine
                search_query: Search in plugin name/description
                limit: Maximum results to return (default: 50)

            Returns:
                JSON with list of plugins and metadata

            Example:
                list_plugins status_filter="published"
                list_plugins machine_group="elasticsearch"
                list_plugins installed_only=true
                list_plugins search_query="kubernetes"
            """
            result = self.plugin_system.list_plugins(
                status_filter=status_filter,
                machine_group=machine_group,
                installed_only=installed_only,
                machine_id=self.machine_id if installed_only else None,
                search_query=search_query,
                limit=limit
            )

            return json.dumps(result, indent=2)

        @self.mcp.tool()
        async def get_plugin_info(plugin_id: str) -> str:
            """
            Get detailed information about a specific plugin.

            Args:
                plugin_id: Plugin ID to get details for

            Returns:
                JSON with complete plugin details including files, dependencies, installations

            Example:
                get_plugin_info plugin_id="plugin_devops-tools_1_0_0"
            """
            plugin = self.plugin_system.get_plugin(plugin_id)

            if not plugin:
                return json.dumps({
                    'success': False,
                    'error': f'Plugin not found: {plugin_id}'
                })

            return json.dumps({
                'success': True,
                'plugin': plugin
            }, indent=2)

        @self.mcp.tool()
        async def get_plugin_status() -> str:
            """
            Get installation status of all plugins on this machine.

            Shows installed plugins, their versions, and available updates.

            Returns:
                JSON with installation status and update information

            Example:
                get_plugin_status
            """
            result = self.plugin_system.get_installation_status(self.machine_id)
            return json.dumps(result, indent=2)

        @self.mcp.tool()
        async def get_plugin_stats() -> str:
            """
            Get plugin system statistics.

            Shows counts of plugins by status, installations, components, etc.

            Returns:
                JSON with plugin system statistics

            Example:
                get_plugin_stats
            """
            stats = self.plugin_system.get_stats()
            return json.dumps({
                'success': True,
                'stats': stats
            }, indent=2)

        # =====================
        # Plugin Sync
        # =====================

        @self.mcp.tool()
        async def sync_plugins(
            force: bool = False,
            auto_install: bool = False
        ) -> str:
            """
            Sync plugins with the hAIveMind collective.

            Checks for new plugins compatible with this machine's group
            and optionally installs them.

            Args:
                force: Force re-sync even if already up to date
                auto_install: Automatically install compatible new plugins

            Returns:
                JSON with sync results

            Example:
                sync_plugins
                sync_plugins auto_install=true
            """
            # Determine this machine's groups
            machine_groups = self.config.get('memory', {}).get('machine_groups', {})
            my_groups = []
            for group_name, machines in machine_groups.items():
                if self.machine_id in machines:
                    my_groups.append(group_name)

            if not my_groups:
                my_groups = ['personal']  # Default group

            # Get current installation status
            current_status = self.plugin_system.get_installation_status(self.machine_id)
            installed_ids = {i['plugin_id'] for i in current_status.get('installations', [])}

            # Find compatible plugins
            compatible_plugins = []
            for group in my_groups:
                plugins = self.plugin_system.get_plugins_for_machine_group(group)
                for p in plugins:
                    if p['id'] not in installed_ids:
                        compatible_plugins.append(p)

            # Remove duplicates
            seen = set()
            unique_plugins = []
            for p in compatible_plugins:
                if p['id'] not in seen:
                    seen.add(p['id'])
                    unique_plugins.append(p)

            installed = []
            if auto_install:
                for plugin in unique_plugins:
                    result = self.plugin_system.install_plugin(
                        plugin_id=plugin['id'],
                        machine_id=self.machine_id
                    )
                    if result.get('success'):
                        installed.append(plugin['name'])

            return json.dumps({
                'success': True,
                'machine_id': self.machine_id,
                'machine_groups': my_groups,
                'current_installations': len(installed_ids),
                'available_plugins': len(unique_plugins),
                'plugins_available': [p['name'] for p in unique_plugins],
                'updates_available': current_status.get('updates_available', []),
                'auto_installed': installed if auto_install else None
            }, indent=2)

        @self.mcp.tool()
        async def get_plugin_sync_payload(plugin_id: str) -> str:
            """
            Get plugin data for syncing to another machine.

            Returns complete plugin data including all files for distribution.
            Used by sync_service for cross-machine plugin distribution.

            Args:
                plugin_id: Plugin ID to get sync payload for

            Returns:
                JSON with complete plugin data for sync

            Example:
                get_plugin_sync_payload plugin_id="plugin_devops-tools_1_0_0"
            """
            payload = self.plugin_system.get_sync_payload(plugin_id)

            if not payload:
                return json.dumps({
                    'success': False,
                    'error': f'Plugin not found: {plugin_id}'
                })

            return json.dumps({
                'success': True,
                'payload': payload
            }, indent=2)

        @self.mcp.tool()
        async def import_plugin_from_sync(sync_payload: str) -> str:
            """
            Import a plugin from sync payload received from another machine.

            Args:
                sync_payload: JSON string of plugin sync payload

            Returns:
                JSON with import status

            Example:
                import_plugin_from_sync sync_payload='{"id": "plugin_...", ...}'
            """
            try:
                payload = json.loads(sync_payload)
            except json.JSONDecodeError as e:
                return json.dumps({
                    'success': False,
                    'error': f'Invalid JSON payload: {e}'
                })

            result = self.plugin_system.import_plugin_from_sync(payload)
            return json.dumps(result, indent=2)

        # =====================
        # Plugin Search
        # =====================

        @self.mcp.tool()
        async def search_plugins(query: str) -> str:
            """
            Search for plugins by name or description.

            Uses text matching to find relevant plugins.

            Args:
                query: Search query string

            Returns:
                JSON with matching plugins

            Example:
                search_plugins query="kubernetes deployment"
                search_plugins query="elasticsearch"
            """
            result = self.plugin_system.list_plugins(
                status_filter=PluginStatus.PUBLISHED.value,
                search_query=query,
                machine_id=self.machine_id
            )

            return json.dumps({
                'success': True,
                'query': query,
                'results': result.get('plugins', []),
                'total': result.get('total', 0)
            }, indent=2)

        @self.mcp.tool()
        async def get_plugins_for_capability(capability: str) -> str:
            """
            Find plugins that provide a specific capability.

            Args:
                capability: Capability to search for (e.g., "elasticsearch_ops", "deployment")

            Returns:
                JSON with plugins providing the capability

            Example:
                get_plugins_for_capability capability="elasticsearch_ops"
                get_plugins_for_capability capability="incident_response"
            """
            # Search in plugin descriptions and required capabilities
            result = self.plugin_system.list_plugins(
                status_filter=PluginStatus.PUBLISHED.value,
                search_query=capability
            )

            # Also check machine groups that match the capability
            machine_groups = self.config.get('memory', {}).get('machine_groups', {})
            capability_groups = []

            # Map capabilities to machine groups
            capability_map = {
                'elasticsearch_ops': 'elasticsearch',
                'database_ops': 'databases',
                'scraping': 'scrapers',
                'deployment': 'orchestrators',
                'monitoring': 'monitoring',
                'development': 'dev_environments'
            }

            if capability.lower() in capability_map:
                group = capability_map[capability.lower()]
                group_plugins = self.plugin_system.get_plugins_for_machine_group(group)

                # Merge results
                existing_ids = {p['id'] for p in result.get('plugins', [])}
                for p in group_plugins:
                    if p['id'] not in existing_ids:
                        result['plugins'].append(p)

            return json.dumps({
                'success': True,
                'capability': capability,
                'plugins': result.get('plugins', [])
            }, indent=2)


def register_plugin_tools(mcp_server, storage, config: Dict[str, Any]) -> PluginMCPTools:
    """
    Register plugin MCP tools with a FastMCP server.

    Args:
        mcp_server: FastMCP server instance
        storage: MemoryStorage instance
        config: Full configuration dict

    Returns:
        PluginMCPTools instance
    """
    return PluginMCPTools(mcp_server, storage, config)
