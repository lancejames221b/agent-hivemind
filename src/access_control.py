"""
Access Control System for hAIveMind

Implements Tailscale-style ACL/Grants with deny-by-default:
- Grant-based access control
- Tag matching (wildcards supported)
- Capability matching
- Confidentiality level enforcement
- Time-based conditions
"""

import re
import fnmatch
import sqlite3
import logging
import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class Permission(Enum):
    """Standard permissions for hAIveMind resources"""
    READ = "READ"
    WRITE = "WRITE"
    DELETE = "DELETE"
    ADMIN = "ADMIN"
    DELEGATE = "DELEGATE"           # Delegate tasks to other agents
    QUERY = "QUERY"                 # Query agent knowledge
    BROADCAST = "BROADCAST"         # Broadcast to collective
    SHARE_VAULT = "SHARE_VAULT"     # Share vault access
    REVOKE = "REVOKE"               # Revoke other agents


class ConfidentialityLevel(Enum):
    """Data confidentiality levels (ordered by sensitivity)"""
    NORMAL = "normal"               # Default, shareable
    INTERNAL = "internal"           # Org-only, no external sync
    CONFIDENTIAL = "confidential"   # Local machine only
    PII = "pii"                     # Personal data, audit-logged

    @classmethod
    def level_order(cls) -> Dict[str, int]:
        return {
            "normal": 0,
            "internal": 1,
            "confidential": 2,
            "pii": 3
        }

    def can_access(self, required: "ConfidentialityLevel") -> bool:
        """Check if this level can access data at the required level"""
        order = self.level_order()
        return order.get(self.value, 0) >= order.get(required.value, 0)


@dataclass
class AccessGrant:
    """ACL Grant definition (Tailscale-style)"""
    grant_id: str
    grant_name: str
    description: Optional[str]
    priority: int                   # Lower = higher priority
    enabled: bool

    # Source (who can access)
    src_agents: List[str]           # Agent ID patterns
    src_tags: List[str]             # Tag patterns (e.g., "tag:elasticsearch")
    src_roles: List[str]            # Role patterns (e.g., "role:hive_mind")
    src_teams: List[str]            # Team IDs

    # Destination (what can be accessed)
    dst_vaults: List[str]           # Vault ID patterns
    dst_memories: List[str]         # Memory category patterns
    dst_agents: List[str]           # Target agent patterns
    dst_resources: List[str]        # Generic resource patterns

    # Permissions
    permissions: List[str]          # List of Permission values

    # Conditions
    conditions: Dict[str, Any]      # Additional conditions

    # Metadata
    created_by: str
    created_at: str
    updated_at: Optional[str]
    expires_at: Optional[str]


@dataclass
class AccessRequest:
    """Request to check access"""
    agent_id: str
    agent_tags: List[str]
    agent_capabilities: List[str]
    agent_roles: List[str] = field(default_factory=list)
    agent_teams: List[str] = field(default_factory=list)
    resource_type: str = ""         # vault, memory, agent, resource
    resource_id: str = ""
    permission: str = ""
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AccessDecision:
    """Result of access check"""
    allowed: bool
    grant_matched: Optional[str] = None
    denial_reason: Optional[str] = None
    conditions_checked: List[str] = field(default_factory=list)
    confidentiality_max: ConfidentialityLevel = ConfidentialityLevel.NORMAL


class AccessControlSystem:
    """
    Deny-by-default Access Control System

    Evaluates ACL grants to determine if an agent can access a resource.
    All access is denied unless explicitly granted.
    """

    def __init__(self, db_path: str = "data/agent_identity.db"):
        """Initialize access control system"""
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    # ==================== Grant Management ====================

    def create_grant(
        self,
        grant_name: str,
        created_by: str,
        permissions: List[str],
        description: Optional[str] = None,
        priority: int = 100,
        src_agents: Optional[List[str]] = None,
        src_tags: Optional[List[str]] = None,
        src_roles: Optional[List[str]] = None,
        src_teams: Optional[List[str]] = None,
        dst_vaults: Optional[List[str]] = None,
        dst_memories: Optional[List[str]] = None,
        dst_agents: Optional[List[str]] = None,
        dst_resources: Optional[List[str]] = None,
        conditions: Optional[Dict[str, Any]] = None,
        expires_hours: Optional[int] = None,
    ) -> Optional[AccessGrant]:
        """
        Create a new access grant

        Args:
            grant_name: Unique name for the grant
            created_by: Admin who created the grant
            permissions: List of permissions to grant
            description: Optional description
            priority: Lower number = higher priority
            src_*: Source patterns (who can access)
            dst_*: Destination patterns (what can be accessed)
            conditions: Additional conditions (mfa_required, time_window, etc.)
            expires_hours: Hours until grant expires

        Returns:
            AccessGrant if created successfully
        """
        try:
            grant_id = f"grant_{secrets.token_hex(8)}"
            expires_at = (datetime.utcnow() + timedelta(hours=expires_hours)).isoformat() if expires_hours else None

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO access_grants (
                    grant_id, grant_name, description, priority, enabled,
                    src_agents, src_tags, src_roles, src_teams,
                    dst_vaults, dst_memories, dst_agents, dst_resources,
                    permissions, conditions, created_by, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                grant_id, grant_name, description, priority, True,
                json.dumps(src_agents or []),
                json.dumps(src_tags or []),
                json.dumps(src_roles or []),
                json.dumps(src_teams or []),
                json.dumps(dst_vaults or []),
                json.dumps(dst_memories or []),
                json.dumps(dst_agents or []),
                json.dumps(dst_resources or []),
                json.dumps(permissions),
                json.dumps(conditions or {}),
                created_by,
                expires_at
            ))

            conn.commit()
            conn.close()

            logger.info(f"Created access grant: {grant_name}")

            return AccessGrant(
                grant_id=grant_id,
                grant_name=grant_name,
                description=description,
                priority=priority,
                enabled=True,
                src_agents=src_agents or [],
                src_tags=src_tags or [],
                src_roles=src_roles or [],
                src_teams=src_teams or [],
                dst_vaults=dst_vaults or [],
                dst_memories=dst_memories or [],
                dst_agents=dst_agents or [],
                dst_resources=dst_resources or [],
                permissions=permissions,
                conditions=conditions or {},
                created_by=created_by,
                created_at=datetime.utcnow().isoformat(),
                updated_at=None,
                expires_at=expires_at
            )

        except sqlite3.IntegrityError:
            logger.error(f"Grant with name '{grant_name}' already exists")
            return None
        except Exception as e:
            logger.error(f"Failed to create grant: {e}")
            return None

    def get_grant(self, grant_id: str) -> Optional[AccessGrant]:
        """Get a grant by ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT grant_id, grant_name, description, priority, enabled,
                       src_agents, src_tags, src_roles, src_teams,
                       dst_vaults, dst_memories, dst_agents, dst_resources,
                       permissions, conditions, created_by, created_at,
                       updated_at, expires_at
                FROM access_grants
                WHERE grant_id = ?
            """, (grant_id,))

            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            return self._row_to_grant(row)

        except Exception as e:
            logger.error(f"Failed to get grant {grant_id}: {e}")
            return None

    def list_grants(self, enabled_only: bool = True) -> List[AccessGrant]:
        """List all grants ordered by priority"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = """
                SELECT grant_id, grant_name, description, priority, enabled,
                       src_agents, src_tags, src_roles, src_teams,
                       dst_vaults, dst_memories, dst_agents, dst_resources,
                       permissions, conditions, created_by, created_at,
                       updated_at, expires_at
                FROM access_grants
            """
            if enabled_only:
                query += " WHERE enabled = TRUE"
            query += " ORDER BY priority ASC"

            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()

            return [self._row_to_grant(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to list grants: {e}")
            return []

    def update_grant(
        self,
        grant_id: str,
        updated_by: str,
        **kwargs
    ) -> bool:
        """Update a grant's fields"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Build update statement dynamically
            updates = ["updated_at = ?"]
            params = [datetime.utcnow().isoformat()]

            field_map = {
                "description": "description",
                "priority": "priority",
                "enabled": "enabled",
                "src_agents": "src_agents",
                "src_tags": "src_tags",
                "src_roles": "src_roles",
                "src_teams": "src_teams",
                "dst_vaults": "dst_vaults",
                "dst_memories": "dst_memories",
                "dst_agents": "dst_agents",
                "dst_resources": "dst_resources",
                "permissions": "permissions",
                "conditions": "conditions",
            }

            for key, value in kwargs.items():
                if key in field_map:
                    updates.append(f"{field_map[key]} = ?")
                    if isinstance(value, (list, dict)):
                        params.append(json.dumps(value))
                    else:
                        params.append(value)

            params.append(grant_id)

            cursor.execute(f"""
                UPDATE access_grants
                SET {', '.join(updates)}
                WHERE grant_id = ?
            """, params)

            conn.commit()
            conn.close()

            logger.info(f"Updated grant {grant_id} by {updated_by}")
            return True

        except Exception as e:
            logger.error(f"Failed to update grant {grant_id}: {e}")
            return False

    def delete_grant(self, grant_id: str) -> bool:
        """Delete a grant"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM access_grants WHERE grant_id = ?", (grant_id,))

            conn.commit()
            conn.close()

            logger.info(f"Deleted grant {grant_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete grant {grant_id}: {e}")
            return False

    def _row_to_grant(self, row: tuple) -> AccessGrant:
        """Convert database row to AccessGrant"""
        return AccessGrant(
            grant_id=row[0],
            grant_name=row[1],
            description=row[2],
            priority=row[3],
            enabled=bool(row[4]),
            src_agents=json.loads(row[5]) if row[5] else [],
            src_tags=json.loads(row[6]) if row[6] else [],
            src_roles=json.loads(row[7]) if row[7] else [],
            src_teams=json.loads(row[8]) if row[8] else [],
            dst_vaults=json.loads(row[9]) if row[9] else [],
            dst_memories=json.loads(row[10]) if row[10] else [],
            dst_agents=json.loads(row[11]) if row[11] else [],
            dst_resources=json.loads(row[12]) if row[12] else [],
            permissions=json.loads(row[13]) if row[13] else [],
            conditions=json.loads(row[14]) if row[14] else {},
            created_by=row[15],
            created_at=row[16],
            updated_at=row[17],
            expires_at=row[18]
        )

    # ==================== Access Evaluation ====================

    def check_access(self, request: AccessRequest) -> AccessDecision:
        """
        Check if an access request is allowed

        This is the main authorization function. It evaluates all grants
        in priority order and returns the first matching grant, or denies
        access if no grants match.

        Args:
            request: AccessRequest with agent info and resource details

        Returns:
            AccessDecision with allowed/denied and reason
        """
        # Get all enabled grants sorted by priority
        grants = self.list_grants(enabled_only=True)

        for grant in grants:
            # Check if grant has expired
            if grant.expires_at:
                if datetime.fromisoformat(grant.expires_at) < datetime.utcnow():
                    continue

            # Check source match (agent must match at least one source pattern)
            if not self._matches_source(request, grant):
                continue

            # Check destination match
            if not self._matches_destination(request, grant):
                continue

            # Check permission
            if request.permission and request.permission not in grant.permissions:
                continue

            # Check conditions
            conditions_result = self._check_conditions(request, grant)
            if not conditions_result[0]:
                continue

            # Grant matched - access allowed
            confidentiality_max = ConfidentialityLevel(
                grant.conditions.get("confidentiality_max", "normal")
            )

            return AccessDecision(
                allowed=True,
                grant_matched=grant.grant_name,
                conditions_checked=conditions_result[1],
                confidentiality_max=confidentiality_max
            )

        # No grant matched - deny by default
        return AccessDecision(
            allowed=False,
            denial_reason="No matching grant found (deny-by-default)"
        )

    def _matches_source(self, request: AccessRequest, grant: AccessGrant) -> bool:
        """Check if the request source matches any grant source pattern"""
        # If no source patterns specified, match all
        if not any([grant.src_agents, grant.src_tags, grant.src_roles, grant.src_teams]):
            return True

        # Check agent ID patterns
        for pattern in grant.src_agents:
            if self._pattern_match(request.agent_id, pattern):
                return True

        # Check tag patterns
        for pattern in grant.src_tags:
            for tag in request.agent_tags:
                if self._pattern_match(tag, pattern):
                    return True

        # Check role patterns
        for pattern in grant.src_roles:
            for role in request.agent_roles:
                if self._pattern_match(role, pattern):
                    return True

        # Check team membership
        for team_id in grant.src_teams:
            if team_id in request.agent_teams:
                return True

        return False

    def _matches_destination(self, request: AccessRequest, grant: AccessGrant) -> bool:
        """Check if the request destination matches any grant destination pattern"""
        # Map resource type to grant field
        type_field_map = {
            "vault": grant.dst_vaults,
            "memory": grant.dst_memories,
            "agent": grant.dst_agents,
            "resource": grant.dst_resources,
        }

        patterns = type_field_map.get(request.resource_type, grant.dst_resources)

        # If no destination patterns for this type, check if grant has any patterns at all
        if not patterns:
            # If grant has no patterns for this type but has patterns for other types, no match
            all_patterns = (
                grant.dst_vaults + grant.dst_memories +
                grant.dst_agents + grant.dst_resources
            )
            if all_patterns:
                return False
            # If grant has no destination patterns at all, match all (open grant)
            return True

        # Check patterns
        for pattern in patterns:
            if self._pattern_match(request.resource_id, pattern):
                return True

        return False

    def _check_conditions(self, request: AccessRequest, grant: AccessGrant) -> Tuple[bool, List[str]]:
        """
        Check grant conditions

        Returns:
            Tuple of (conditions_met, list of checked conditions)
        """
        conditions = grant.conditions
        checked = []

        # MFA required
        if conditions.get("mfa_required"):
            checked.append("mfa_required")
            if not request.context.get("mfa_verified"):
                return False, checked

        # Time window
        if "time_window" in conditions:
            checked.append("time_window")
            tw = conditions["time_window"]
            now = datetime.utcnow()

            # Check day of week
            if "days" in tw:
                day_names = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
                current_day = day_names[now.weekday()]
                if current_day not in tw["days"]:
                    return False, checked

            # Check hour range
            if "hours" in tw:
                hour_start = tw["hours"].get("start", 0)
                hour_end = tw["hours"].get("end", 24)
                if not (hour_start <= now.hour < hour_end):
                    return False, checked

        # Confidentiality level
        if "confidentiality_max" in conditions:
            checked.append("confidentiality_max")
            max_level = ConfidentialityLevel(conditions["confidentiality_max"])
            request_level = ConfidentialityLevel(
                request.context.get("resource_confidentiality", "normal")
            )
            if not max_level.can_access(request_level):
                return False, checked

        # IP whitelist
        if "ip_whitelist" in conditions:
            checked.append("ip_whitelist")
            client_ip = request.context.get("client_ip")
            if client_ip and client_ip not in conditions["ip_whitelist"]:
                return False, checked

        # Machine whitelist
        if "machine_whitelist" in conditions:
            checked.append("machine_whitelist")
            machine_id = request.context.get("machine_id")
            if machine_id and machine_id not in conditions["machine_whitelist"]:
                return False, checked

        # Required capability
        if "required_capability" in conditions:
            checked.append("required_capability")
            required = conditions["required_capability"]
            if isinstance(required, str):
                required = [required]
            if not any(cap in request.agent_capabilities for cap in required):
                return False, checked

        # Custom condition checker (extensible)
        if "custom" in conditions:
            checked.append("custom")
            # Custom conditions would be evaluated by a pluggable system
            # For now, just pass
            pass

        return True, checked

    def _pattern_match(self, value: str, pattern: str) -> bool:
        """
        Match a value against a pattern

        Supports:
        - Exact match: "agent123" matches "agent123"
        - Wildcard: "agent*" matches "agent123", "agent456"
        - Double wildcard: "**" matches anything
        - Prefix: "tag:" matches "tag:elasticsearch"
        """
        # Double wildcard matches everything
        if pattern == "**" or pattern == "*":
            return True

        # Strip common prefixes for comparison
        for prefix in ["tag:", "role:", "vault:", "memory:", "agent:", "resource:"]:
            if pattern.startswith(prefix):
                pattern = pattern[len(prefix):]
            if value.startswith(prefix):
                value = value[len(prefix):]

        # Use fnmatch for glob-style matching
        return fnmatch.fnmatch(value, pattern)

    # ==================== Convenience Methods ====================

    def can_read(self, request: AccessRequest) -> bool:
        """Check if agent can read a resource"""
        request.permission = Permission.READ.value
        return self.check_access(request).allowed

    def can_write(self, request: AccessRequest) -> bool:
        """Check if agent can write to a resource"""
        request.permission = Permission.WRITE.value
        return self.check_access(request).allowed

    def can_delete(self, request: AccessRequest) -> bool:
        """Check if agent can delete a resource"""
        request.permission = Permission.DELETE.value
        return self.check_access(request).allowed

    def can_delegate(self, request: AccessRequest) -> bool:
        """Check if agent can delegate tasks"""
        request.permission = Permission.DELEGATE.value
        return self.check_access(request).allowed

    def can_share_vault(self, request: AccessRequest) -> bool:
        """Check if agent can share vault access"""
        request.permission = Permission.SHARE_VAULT.value
        return self.check_access(request).allowed

    def get_agent_permissions(
        self,
        agent_id: str,
        agent_tags: List[str],
        agent_capabilities: List[str],
        resource_type: str,
        resource_id: str
    ) -> Set[str]:
        """Get all permissions an agent has for a resource"""
        permissions = set()

        for perm in Permission:
            request = AccessRequest(
                agent_id=agent_id,
                agent_tags=agent_tags,
                agent_capabilities=agent_capabilities,
                resource_type=resource_type,
                resource_id=resource_id,
                permission=perm.value
            )
            if self.check_access(request).allowed:
                permissions.add(perm.value)

        return permissions

    # ==================== Default Grants ====================

    def create_default_grants(self, admin_id: str = "system"):
        """Create default access grants for common scenarios"""

        # Admin full access
        self.create_grant(
            grant_name="admin-full-access",
            created_by=admin_id,
            description="Full access for administrators",
            priority=1,
            src_tags=["tag:admin", "role:admin"],
            dst_resources=["**"],
            permissions=[p.value for p in Permission],
            conditions={"mfa_required": True}
        )

        # Self-access for all agents
        self.create_grant(
            grant_name="agent-self-access",
            created_by=admin_id,
            description="Agents can access their own resources",
            priority=10,
            src_agents=["*"],
            dst_agents=["${src_agent}"],  # Template: matches source agent
            permissions=[Permission.READ.value, Permission.WRITE.value],
        )

        # Orchestrators can delegate
        self.create_grant(
            grant_name="orchestrator-delegation",
            created_by=admin_id,
            description="Orchestrators can delegate tasks to other agents",
            priority=20,
            src_tags=["tag:orchestrator", "role:hive_mind"],
            dst_agents=["*"],
            permissions=[Permission.DELEGATE.value, Permission.QUERY.value],
        )

        # Elasticsearch agents access infrastructure memories
        self.create_grant(
            grant_name="elasticsearch-infrastructure",
            created_by=admin_id,
            description="ES agents can access infrastructure memories",
            priority=30,
            src_tags=["tag:elasticsearch"],
            dst_memories=["memory:infrastructure/*", "memory:monitoring/*"],
            permissions=[Permission.READ.value, Permission.WRITE.value],
            conditions={"confidentiality_max": "internal"}
        )

        # Development agents have broad read access
        self.create_grant(
            grant_name="dev-read-access",
            created_by=admin_id,
            description="Development agents can read most resources",
            priority=50,
            src_tags=["tag:development", "tag:dev"],
            dst_memories=["**"],
            dst_vaults=["vault:dev-*", "vault:staging-*"],
            permissions=[Permission.READ.value],
            conditions={
                "confidentiality_max": "internal",
                "time_window": {
                    "days": ["mon", "tue", "wed", "thu", "fri"],
                    "hours": {"start": 6, "end": 22}
                }
            }
        )

        # Broadcast permission for all active agents
        self.create_grant(
            grant_name="collective-broadcast",
            created_by=admin_id,
            description="All active agents can broadcast to collective",
            priority=60,
            src_agents=["*"],
            dst_resources=["broadcast:*"],
            permissions=[Permission.BROADCAST.value],
            conditions={"confidentiality_max": "internal"}
        )

        logger.info("Created default access grants")


# Singleton instance
_access_control_system: Optional[AccessControlSystem] = None


def get_access_control_system() -> AccessControlSystem:
    """Get or create the access control system singleton"""
    global _access_control_system
    if _access_control_system is None:
        _access_control_system = AccessControlSystem()
    return _access_control_system
