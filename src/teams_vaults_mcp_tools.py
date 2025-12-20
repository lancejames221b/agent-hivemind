"""
Teams and Vaults MCP Tools

MCP tool definitions and handlers for team collaboration and vault management.
"""

from typing import Dict, List, Optional, Any
import logging
from mcp.types import Tool
from teams_and_vaults_system import (
    TeamsAndVaultsSystem,
    TeamRole,
    VaultType,
    AccessLevel,
    AccessMode
)

logger = logging.getLogger(__name__)


def get_teams_vaults_tools() -> List[Tool]:
    """
    Get list of Teams & Vaults MCP tools.

    Returns tools for:
    - Mode management (solo/vault/team)
    - Team creation and membership
    - Vault management and secrets
    - Access control and audit
    """

    return [
        # ==================== Mode Management Tools ====================

        Tool(
            name="get_mode",
            description="""
Get your current operating mode and context.

Returns:
- mode: Current mode (solo/vault/team)
- context: Active team or vault details
- permissions: What you can do in this mode
- available_modes: All modes you can switch to

Use this to understand your current access context before storing or retrieving memories.
            """.strip(),
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Agent identifier (auto-detected if not provided)"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User identifier (auto-detected if not provided)"
                    }
                },
                "required": []
            }
        ),

        Tool(
            name="set_mode",
            description="""
Switch your operating mode.

MODE BEHAVIOR:
- "solo": Work privately - memories are only visible to you (DEFAULT - safest)
- "vault": Access encrypted vault for secrets and credentials
- "team": Work collaboratively - memories shared with team members

Your mode persists across tool calls until changed.

Examples:
- Personal work: set_mode(mode="solo")
- Access secrets: set_mode(mode="vault", context_id="vault_prod_secrets")
- Team collaboration: set_mode(mode="team", context_id="team_design_001")
            """.strip(),
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["solo", "vault", "team"],
                        "description": "Operating mode to switch to"
                    },
                    "context_id": {
                        "type": "string",
                        "description": "Team ID or Vault ID (required for vault/team modes)"
                    },
                    "agent_id": {
                        "type": "string",
                        "description": "Agent identifier (auto-detected if not provided)"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User identifier (auto-detected if not provided)"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Optional metadata for mode switch"
                    }
                },
                "required": ["mode"]
            }
        ),

        Tool(
            name="list_available_modes",
            description="""
List all modes and contexts available to current user.

Returns all teams you're a member of and vaults you have access to,
allowing you to switch between solo, vault, and team modes.
            """.strip(),
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User identifier (auto-detected if not provided)"
                    }
                },
                "required": []
            }
        ),

        # ==================== Team Management Tools ====================

        Tool(
            name="create_team",
            description="""
Create a new team for collaborative work.

Teams enable:
- Shared memory workspace
- Role-based access control (owner, admin, member, readonly, guest)
- Team activity tracking
- Collaborative agent coordination

You become the team owner and can invite other members.
            """.strip(),
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Team name (e.g., 'Design Team', 'DevOps')"
                    },
                    "description": {
                        "type": "string",
                        "description": "Team purpose and description"
                    },
                    "owner_id": {
                        "type": "string",
                        "description": "Team owner user ID (auto-detected if not provided)"
                    },
                    "settings": {
                        "type": "object",
                        "description": "Team settings (optional)"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Team metadata (optional)"
                    }
                },
                "required": ["name", "description"]
            }
        ),

        Tool(
            name="list_teams",
            description="""
List teams you belong to.

Returns all teams where you are a member, with details about:
- Team name and description
- Your role in the team
- Number of members
- Recent activity
            """.strip(),
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User identifier (auto-detected if not provided)"
                    },
                    "include_details": {
                        "type": "boolean",
                        "description": "Include member counts and activity",
                        "default": True
                    }
                },
                "required": []
            }
        ),

        Tool(
            name="get_team",
            description="""
Get detailed information about a specific team.

Returns:
- Team details (name, description, settings)
- Complete member list with roles
- Recent team activity
- Team vaults
            """.strip(),
            inputSchema={
                "type": "object",
                "properties": {
                    "team_id": {
                        "type": "string",
                        "description": "Team identifier"
                    },
                    "include_members": {
                        "type": "boolean",
                        "description": "Include member list",
                        "default": True
                    },
                    "include_activity": {
                        "type": "boolean",
                        "description": "Include recent activity",
                        "default": True
                    }
                },
                "required": ["team_id"]
            }
        ),

        Tool(
            name="add_team_member",
            description="""
Add a member to a team (requires admin role).

Roles:
- owner: Full control, can delete team
- admin: Manage members and settings
- member: Read/write access to team memories
- readonly: Read-only access
- guest: Limited temporary access
            """.strip(),
            inputSchema={
                "type": "object",
                "properties": {
                    "team_id": {
                        "type": "string",
                        "description": "Team identifier"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User ID to add as member"
                    },
                    "role": {
                        "type": "string",
                        "enum": ["admin", "member", "readonly", "guest"],
                        "description": "Member role",
                        "default": "member"
                    },
                    "invited_by": {
                        "type": "string",
                        "description": "Inviter user ID (auto-detected if not provided)"
                    },
                    "capabilities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific capabilities for this member"
                    }
                },
                "required": ["team_id", "user_id"]
            }
        ),

        Tool(
            name="remove_team_member",
            description="""
Remove a member from a team (requires admin role).

Cannot remove the team owner. Owner must transfer ownership first.
            """.strip(),
            inputSchema={
                "type": "object",
                "properties": {
                    "team_id": {
                        "type": "string",
                        "description": "Team identifier"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User ID to remove"
                    },
                    "removed_by": {
                        "type": "string",
                        "description": "Admin performing removal (auto-detected if not provided)"
                    }
                },
                "required": ["team_id", "user_id"]
            }
        ),

        Tool(
            name="get_team_activity",
            description="""
Get recent team activity and shared memories.

Shows:
- Member joins/leaves
- Memory storage events
- Mode switches
- Access changes
            """.strip(),
            inputSchema={
                "type": "object",
                "properties": {
                    "team_id": {
                        "type": "string",
                        "description": "Team identifier"
                    },
                    "hours": {
                        "type": "integer",
                        "description": "Time window in hours",
                        "default": 24
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum activity entries",
                        "default": 50
                    }
                },
                "required": ["team_id"]
            }
        ),

        # ==================== Vault Management Tools ====================

        Tool(
            name="create_vault",
            description="""
Create a new vault for secure secret storage.

Vault types:
- personal: Private vault for your secrets only
- team: Shared vault for team secrets
- project: Project-specific vault
- shared: Cross-team shared vault

All secrets are encrypted with AES-GCM and audited on access.
            """.strip(),
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Vault name (e.g., 'Production Secrets', 'Personal Vault')"
                    },
                    "vault_type": {
                        "type": "string",
                        "enum": ["personal", "team", "project", "shared"],
                        "description": "Type of vault",
                        "default": "personal"
                    },
                    "owner_id": {
                        "type": "string",
                        "description": "Vault owner (auto-detected if not provided)"
                    },
                    "team_id": {
                        "type": "string",
                        "description": "Team ID (required for team vaults)"
                    },
                    "access_policy": {
                        "type": "object",
                        "description": "Access policy configuration"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Vault metadata"
                    }
                },
                "required": ["name"]
            }
        ),

        Tool(
            name="list_vaults",
            description="""
List all vaults you have access to.

Returns vaults you own or have been granted access to, including:
- Personal vaults
- Team vaults you're a member of
- Shared vaults with explicit grants
            """.strip(),
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User identifier (auto-detected if not provided)"
                    },
                    "vault_type": {
                        "type": "string",
                        "enum": ["personal", "team", "project", "shared"],
                        "description": "Filter by vault type"
                    }
                },
                "required": []
            }
        ),

        Tool(
            name="store_in_vault",
            description="""
Store a secret in a vault with encryption.

IMPORTANT:
- All secrets are encrypted with AES-GCM
- Access is logged for audit trail
- You must provide an audit reason when retrieving

Use this for:
- API keys and credentials
- Database passwords
- SSH keys
- Any sensitive configuration

Examples:
- API key: store_in_vault(vault_id="...", key="stripe_api_key", value="sk_live_...")
- Password: store_in_vault(vault_id="...", key="db_password", value="...")
            """.strip(),
            inputSchema={
                "type": "object",
                "properties": {
                    "vault_id": {
                        "type": "string",
                        "description": "Vault identifier"
                    },
                    "key": {
                        "type": "string",
                        "description": "Secret name/identifier (e.g., 'api_key', 'db_password')"
                    },
                    "value": {
                        "type": "string",
                        "description": "Secret value (will be encrypted)"
                    },
                    "created_by": {
                        "type": "string",
                        "description": "Creator user ID (auto-detected if not provided)"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Secret metadata (type, environment, etc.)"
                    },
                    "expires_at": {
                        "type": "string",
                        "description": "Expiration timestamp (ISO 8601)"
                    }
                },
                "required": ["vault_id", "key", "value"]
            }
        ),

        Tool(
            name="retrieve_from_vault",
            description="""
Retrieve and decrypt a secret from a vault.

IMPORTANT:
- Requires read access to the vault
- All retrievals are logged in audit trail
- You MUST provide an audit_reason for compliance

The secret will be decrypted and returned in plaintext.
Handle with care - do not log or store decrypted secrets.
            """.strip(),
            inputSchema={
                "type": "object",
                "properties": {
                    "vault_id": {
                        "type": "string",
                        "description": "Vault identifier"
                    },
                    "key": {
                        "type": "string",
                        "description": "Secret name to retrieve"
                    },
                    "actor_id": {
                        "type": "string",
                        "description": "User retrieving secret (auto-detected if not provided)"
                    },
                    "audit_reason": {
                        "type": "string",
                        "description": "REQUIRED: Reason for accessing this secret (for audit log)"
                    }
                },
                "required": ["vault_id", "key", "audit_reason"]
            }
        ),

        Tool(
            name="list_vault_secrets",
            description="""
List all secret keys in a vault (not values).

Returns secret metadata only - keys, creation dates, expiry.
Does not return secret values (use retrieve_from_vault for that).
            """.strip(),
            inputSchema={
                "type": "object",
                "properties": {
                    "vault_id": {
                        "type": "string",
                        "description": "Vault identifier"
                    }
                },
                "required": ["vault_id"]
            }
        ),

        Tool(
            name="delete_vault_secret",
            description="""
Delete a secret from a vault.

WARNING: This permanently deletes the secret.
Deletion is logged in audit trail.
            """.strip(),
            inputSchema={
                "type": "object",
                "properties": {
                    "vault_id": {
                        "type": "string",
                        "description": "Vault identifier"
                    },
                    "key": {
                        "type": "string",
                        "description": "Secret name to delete"
                    },
                    "actor_id": {
                        "type": "string",
                        "description": "User performing deletion (auto-detected if not provided)"
                    }
                },
                "required": ["vault_id", "key"]
            }
        ),

        # ==================== Access Control Tools ====================

        Tool(
            name="share_vault",
            description="""
Share vault access with a user or team.

Access levels:
- read: Can retrieve secrets
- write: Can add/modify secrets
- admin: Can manage vault and grant access

Optionally set expiration for temporary access.
            """.strip(),
            inputSchema={
                "type": "object",
                "properties": {
                    "vault_id": {
                        "type": "string",
                        "description": "Vault identifier"
                    },
                    "share_with": {
                        "type": "string",
                        "description": "User ID or Team ID to share with"
                    },
                    "share_type": {
                        "type": "string",
                        "enum": ["user", "team"],
                        "description": "Whether sharing with user or team",
                        "default": "user"
                    },
                    "access_level": {
                        "type": "string",
                        "enum": ["read", "write", "admin"],
                        "description": "Access level to grant",
                        "default": "read"
                    },
                    "granted_by": {
                        "type": "string",
                        "description": "Grantor user ID (auto-detected if not provided)"
                    },
                    "expires_at": {
                        "type": "string",
                        "description": "Expiration timestamp for temporary access (ISO 8601)"
                    }
                },
                "required": ["vault_id", "share_with"]
            }
        ),

        Tool(
            name="vault_audit_log",
            description="""
Get vault access audit log.

Shows all vault operations:
- Secret reads
- Secret writes
- Access grants
- Vault creation/deletion

Essential for security compliance and incident investigation.
            """.strip(),
            inputSchema={
                "type": "object",
                "properties": {
                    "vault_id": {
                        "type": "string",
                        "description": "Vault identifier"
                    },
                    "hours": {
                        "type": "integer",
                        "description": "Time window in hours",
                        "default": 24
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum log entries",
                        "default": 100
                    },
                    "action_filter": {
                        "type": "string",
                        "description": "Filter by action type (read, write, share, etc.)"
                    }
                },
                "required": ["vault_id"]
            }
        ),
    ]


class TeamsVaultsMCPTools:
    """Handler for Teams & Vaults MCP tools"""

    def __init__(self, system: TeamsAndVaultsSystem, default_user_id: str, default_agent_id: str):
        self.system = system
        self.default_user_id = default_user_id
        self.default_agent_id = default_agent_id

    def _get_user_id(self, user_id: Optional[str]) -> str:
        """Get user ID with fallback to default"""
        return user_id or self.default_user_id

    def _get_agent_id(self, agent_id: Optional[str]) -> str:
        """Get agent ID with fallback to default"""
        return agent_id or self.default_agent_id

    # ==================== Mode Management ====================

    async def handle_get_mode(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get current operating mode"""
        agent_id = self._get_agent_id(arguments.get('agent_id'))
        user_id = self._get_user_id(arguments.get('user_id'))

        mode_data = self.system.get_mode(agent_id, user_id)

        if not mode_data:
            # Default to solo mode
            return {
                "mode": "solo",
                "message": "No active mode - defaulted to solo (private)",
                "available_modes": await self.handle_list_available_modes({"user_id": user_id})
            }

        # Enrich with context details
        context_details = {}
        if mode_data['mode'] == 'team' and mode_data.get('context_id'):
            team = self.system.get_team(mode_data['context_id'])
            if team:
                context_details['team'] = {
                    'id': team.team_id,
                    'name': team.name,
                    'description': team.description
                }
        elif mode_data['mode'] == 'vault' and mode_data.get('context_id'):
            vault = self.system.get_vault(mode_data['context_id'])
            if vault:
                context_details['vault'] = {
                    'id': vault.vault_id,
                    'name': vault.name,
                    'type': vault.vault_type
                }

        return {
            **mode_data,
            **context_details,
            "hint": self._get_mode_hint(mode_data['mode'])
        }

    def _get_mode_hint(self, mode: str) -> str:
        """Get helpful hint about current mode"""
        hints = {
            "solo": "You are in SOLO mode. Memories are private to you only.",
            "vault": "You are in VAULT mode. Working with encrypted secrets.",
            "team": "You are in TEAM mode. Memories are shared with team members."
        }
        return hints.get(mode, "")

    async def handle_set_mode(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Set operating mode"""
        agent_id = self._get_agent_id(arguments.get('agent_id'))
        user_id = self._get_user_id(arguments.get('user_id'))
        mode = arguments['mode']
        context_id = arguments.get('context_id')
        metadata = arguments.get('metadata', {})

        # Validate context_id requirements
        if mode in ['vault', 'team'] and not context_id:
            return {
                "error": f"context_id is required for {mode} mode",
                "hint": f"Provide vault_id for vault mode or team_id for team mode"
            }

        # Validate access
        if mode == 'team' and context_id:
            membership = self.system.check_team_membership(context_id, user_id)
            if not membership:
                return {
                    "error": f"You are not a member of team {context_id}",
                    "hint": "Ask a team admin to add you as a member"
                }

        if mode == 'vault' and context_id:
            has_access = self.system.check_vault_access(context_id, user_id, "read")
            if not has_access:
                return {
                    "error": f"You do not have access to vault {context_id}",
                    "hint": "Ask the vault owner to grant you access"
                }

        # Set mode
        result = self.system.set_mode(agent_id, user_id, mode, context_id, metadata)

        return {
            "success": True,
            "mode": mode,
            "context_id": context_id,
            "updated_at": result['updated_at'],
            "message": f"Switched to {mode} mode",
            "hint": self._get_mode_hint(mode)
        }

    async def handle_list_available_modes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List available modes and contexts"""
        user_id = self._get_user_id(arguments.get('user_id'))

        # Get teams
        teams = self.system.list_teams(user_id)
        team_list = [{
            'id': t.team_id,
            'name': t.name,
            'description': t.description
        } for t in teams]

        # Get vaults
        vaults = self.system.list_vaults(user_id)
        vault_list = [{
            'id': v.vault_id,
            'name': v.name,
            'type': v.vault_type
        } for v in vaults]

        return {
            "modes": [
                {
                    "mode": "solo",
                    "description": "Personal work, private memories",
                    "available": True
                },
                {
                    "mode": "vault",
                    "description": "Access encrypted vaults",
                    "available": len(vault_list) > 0,
                    "vaults": vault_list
                },
                {
                    "mode": "team",
                    "description": "Collaborative team work",
                    "available": len(team_list) > 0,
                    "teams": team_list
                }
            ]
        }

    # Additional handlers would go here...
    # (create_team, list_teams, add_team_member, create_vault, store_in_vault, etc.)
    # For brevity, showing structure - full implementation would include all handlers
