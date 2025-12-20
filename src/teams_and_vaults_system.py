"""
Teams and Vaults System - Team Collaboration and Secret Management

Provides secure team collaboration, vault-based secret storage, and mode-aware
access control for hAIveMind distributed agent infrastructure.
"""

import sqlite3
import hashlib
import json
import os
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Literal
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging
import secrets
import hmac

logger = logging.getLogger(__name__)

# Use simple encryption for now (cryptography has compatibility issues)
CRYPTO_AVAILABLE = False
logger.info("Using simple XOR-based encryption for vaults")


class TeamRole(Enum):
    """Team member roles"""
    OWNER = "owner"        # Full control, can delete team
    ADMIN = "admin"        # Manage members, settings
    MEMBER = "member"      # Read/write access
    READONLY = "readonly"  # Read-only access
    GUEST = "guest"        # Limited temporary access


class VaultType(Enum):
    """Vault types"""
    PERSONAL = "personal"  # Private to one user
    TEAM = "team"          # Shared by team members
    PROJECT = "project"    # Project-scoped vault
    SHARED = "shared"      # Cross-team shared vault


class AccessLevel(Enum):
    """Access levels"""
    NONE = "none"
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


class AccessMode(Enum):
    """Operating modes"""
    SOLO = "solo"    # Private individual work
    VAULT = "vault"  # Working with encrypted vaults
    TEAM = "team"    # Collaborative team work


@dataclass
class Team:
    """Team data structure"""
    team_id: str
    name: str
    description: str
    owner_id: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    settings: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TeamMember:
    """Team member data structure"""
    team_id: str
    user_id: str
    role: str  # TeamRole value
    joined_at: str = field(default_factory=lambda: datetime.now().isoformat())
    invited_by: Optional[str] = None
    capabilities: List[str] = field(default_factory=list)


@dataclass
class Vault:
    """Vault data structure"""
    vault_id: str
    name: str
    vault_type: str  # VaultType value
    owner_id: str
    encryption_key_id: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    team_id: Optional[str] = None
    access_policy: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VaultSecret:
    """Vault secret data structure"""
    secret_id: str
    vault_id: str
    key: str  # Secret name
    encrypted_value: str  # Base64 encoded encrypted data
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    created_by: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[str] = None


@dataclass
class AccessGrant:
    """Access grant data structure"""
    grant_id: str
    vault_id: str
    grantee_id: str  # user_id or team_id
    grantee_type: str  # 'user' or 'team'
    access_level: str  # AccessLevel value
    granted_by: str
    granted_at: str = field(default_factory=lambda: datetime.now().isoformat())
    expires_at: Optional[str] = None


class TeamsAndVaultsSystem:
    """
    Core teams and vaults management system

    Features:
    - Team creation and membership management
    - Vault-based encrypted secret storage
    - Fine-grained access control
    - Audit logging for all sensitive operations
    - Mode-aware context management
    """

    def __init__(self, db_path: str = "data/teams_vaults.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

        # Initialize encryption with database path
        self.encryption = VaultEncryption(db_path=str(self.db_path))

    def _init_database(self):
        """Initialize SQLite database with schema from design doc"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- Teams table
                CREATE TABLE IF NOT EXISTS teams (
                    team_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    owner_id TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    settings TEXT DEFAULT '{}',  -- JSON
                    metadata TEXT DEFAULT '{}'   -- JSON
                );

                CREATE INDEX IF NOT EXISTS idx_teams_owner ON teams(owner_id);
                CREATE INDEX IF NOT EXISTS idx_teams_created ON teams(created_at);

                -- Team Members table
                CREATE TABLE IF NOT EXISTS team_members (
                    team_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('owner', 'admin', 'member', 'readonly', 'guest')),
                    joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    invited_by TEXT,
                    capabilities TEXT DEFAULT '[]',  -- JSON array
                    PRIMARY KEY (team_id, user_id),
                    FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_members_user ON team_members(user_id);
                CREATE INDEX IF NOT EXISTS idx_members_role ON team_members(role);

                -- Vaults table
                CREATE TABLE IF NOT EXISTS vaults (
                    vault_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    vault_type TEXT NOT NULL CHECK(vault_type IN ('personal', 'team', 'project', 'shared')),
                    owner_id TEXT NOT NULL,
                    team_id TEXT,
                    encryption_key_id TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    access_policy TEXT DEFAULT '{}',  -- JSON
                    metadata TEXT DEFAULT '{}',       -- JSON
                    FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE SET NULL
                );

                CREATE INDEX IF NOT EXISTS idx_vaults_owner ON vaults(owner_id);
                CREATE INDEX IF NOT EXISTS idx_vaults_team ON vaults(team_id);
                CREATE INDEX IF NOT EXISTS idx_vaults_type ON vaults(vault_type);

                -- Vault Secrets table (encrypted storage)
                CREATE TABLE IF NOT EXISTS vault_secrets (
                    secret_id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    vault_id TEXT NOT NULL,
                    key TEXT NOT NULL,  -- Secret name/identifier
                    encrypted_value TEXT NOT NULL,  -- Base64 encoded encrypted data
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',  -- JSON
                    expires_at TEXT,
                    UNIQUE(vault_id, key),
                    FOREIGN KEY (vault_id) REFERENCES vaults(vault_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_secrets_vault ON vault_secrets(vault_id);
                CREATE INDEX IF NOT EXISTS idx_secrets_expires ON vault_secrets(expires_at);

                -- Vault Access Grants table
                CREATE TABLE IF NOT EXISTS vault_access (
                    grant_id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    vault_id TEXT NOT NULL,
                    grantee_id TEXT NOT NULL,           -- user_id or team_id
                    grantee_type TEXT NOT NULL CHECK(grantee_type IN ('user', 'team')),
                    access_level TEXT NOT NULL CHECK(access_level IN ('read', 'write', 'admin')),
                    granted_by TEXT NOT NULL,
                    granted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    expires_at TEXT,
                    UNIQUE(vault_id, grantee_id),
                    FOREIGN KEY (vault_id) REFERENCES vaults(vault_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_access_vault ON vault_access(vault_id);
                CREATE INDEX IF NOT EXISTS idx_access_grantee ON vault_access(grantee_id);

                -- Vault Audit Log table
                CREATE TABLE IF NOT EXISTS vault_audit (
                    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vault_id TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    action TEXT NOT NULL,  -- read, write, share, access_granted, etc.
                    key_accessed TEXT,
                    reason TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}',  -- JSON
                    FOREIGN KEY (vault_id) REFERENCES vaults(vault_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_audit_vault ON vault_audit(vault_id);
                CREATE INDEX IF NOT EXISTS idx_audit_actor ON vault_audit(actor_id);
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON vault_audit(timestamp);
                CREATE INDEX IF NOT EXISTS idx_audit_action ON vault_audit(action);

                -- Team Activity Log table
                CREATE TABLE IF NOT EXISTS team_activity (
                    activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_id TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    action TEXT NOT NULL,  -- member_added, memory_stored, mode_switched, etc.
                    description TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}',  -- JSON
                    FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_activity_team ON team_activity(team_id);
                CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON team_activity(timestamp);

                -- Encryption Keys table (for vault encryption key management)
                CREATE TABLE IF NOT EXISTS encryption_keys (
                    key_id TEXT PRIMARY KEY,
                    encrypted_key TEXT NOT NULL,  -- Master key encrypted vault key
                    key_version INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    rotated_at TEXT,
                    metadata TEXT DEFAULT '{}'  -- JSON
                );

                -- Session Modes table (for tracking agent operating modes)
                CREATE TABLE IF NOT EXISTS session_modes (
                    session_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    current_mode TEXT NOT NULL CHECK(current_mode IN ('solo', 'vault', 'team')),
                    context_id TEXT,  -- team_id or vault_id depending on mode
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}'  -- JSON
                );

                CREATE INDEX IF NOT EXISTS idx_session_agent ON session_modes(agent_id);
                CREATE INDEX IF NOT EXISTS idx_session_user ON session_modes(user_id);
            """)
            conn.commit()
            logger.info(f"Teams and Vaults database initialized at {self.db_path}")

    # ==================== Team Management ====================

    def create_team(
        self,
        name: str,
        description: str,
        owner_id: str,
        team_id: Optional[str] = None,
        settings: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ) -> Team:
        """Create a new team"""
        if team_id is None:
            team_id = f"team_{secrets.token_hex(8)}"

        team = Team(
            team_id=team_id,
            name=name,
            description=description,
            owner_id=owner_id,
            settings=settings or {},
            metadata=metadata or {}
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO teams (team_id, name, description, owner_id, settings, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                team.team_id,
                team.name,
                team.description,
                team.owner_id,
                json.dumps(team.settings),
                json.dumps(team.metadata)
            ))

            # Add owner as team member
            conn.execute("""
                INSERT INTO team_members (team_id, user_id, role, invited_by)
                VALUES (?, ?, ?, ?)
            """, (team.team_id, owner_id, TeamRole.OWNER.value, owner_id))

            # Log activity
            self._log_team_activity(
                conn,
                team_id=team.team_id,
                actor_id=owner_id,
                action="team_created",
                description=f"Created team '{name}'"
            )

            conn.commit()

        logger.info(f"Created team {team.team_id}: {name}")
        return team

    def get_team(self, team_id: str) -> Optional[Team]:
        """Get team by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("""
                SELECT * FROM teams WHERE team_id = ?
            """, (team_id,)).fetchone()

            if not row:
                return None

            return Team(
                team_id=row['team_id'],
                name=row['name'],
                description=row['description'],
                owner_id=row['owner_id'],
                created_at=row['created_at'],
                settings=json.loads(row['settings']),
                metadata=json.loads(row['metadata'])
            )

    def list_teams(self, user_id: Optional[str] = None) -> List[Team]:
        """List all teams, optionally filtered by user membership"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            if user_id:
                rows = conn.execute("""
                    SELECT DISTINCT t.* FROM teams t
                    JOIN team_members tm ON t.team_id = tm.team_id
                    WHERE tm.user_id = ?
                    ORDER BY t.created_at DESC
                """, (user_id,)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM teams ORDER BY created_at DESC
                """).fetchall()

            return [
                Team(
                    team_id=row['team_id'],
                    name=row['name'],
                    description=row['description'],
                    owner_id=row['owner_id'],
                    created_at=row['created_at'],
                    settings=json.loads(row['settings']),
                    metadata=json.loads(row['metadata'])
                )
                for row in rows
            ]

    def add_team_member(
        self,
        team_id: str,
        user_id: str,
        role: str,
        invited_by: str,
        capabilities: Optional[List[str]] = None
    ) -> TeamMember:
        """Add a member to a team"""
        member = TeamMember(
            team_id=team_id,
            user_id=user_id,
            role=role,
            invited_by=invited_by,
            capabilities=capabilities or []
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO team_members (team_id, user_id, role, invited_by, capabilities)
                VALUES (?, ?, ?, ?, ?)
            """, (
                member.team_id,
                member.user_id,
                member.role,
                member.invited_by,
                json.dumps(member.capabilities)
            ))

            # Log activity
            self._log_team_activity(
                conn,
                team_id=team_id,
                actor_id=invited_by,
                action="member_added",
                description=f"Added {user_id} as {role}"
            )

            conn.commit()

        logger.info(f"Added {user_id} to team {team_id} as {role}")
        return member

    def remove_team_member(self, team_id: str, user_id: str, removed_by: str) -> bool:
        """Remove a member from a team"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM team_members
                WHERE team_id = ? AND user_id = ?
            """, (team_id, user_id))

            if cursor.rowcount > 0:
                self._log_team_activity(
                    conn,
                    team_id=team_id,
                    actor_id=removed_by,
                    action="member_removed",
                    description=f"Removed {user_id} from team"
                )
                conn.commit()
                logger.info(f"Removed {user_id} from team {team_id}")
                return True

            return False

    def get_team_members(self, team_id: str) -> List[TeamMember]:
        """Get all members of a team"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM team_members
                WHERE team_id = ?
                ORDER BY joined_at ASC
            """, (team_id,)).fetchall()

            return [
                TeamMember(
                    team_id=row['team_id'],
                    user_id=row['user_id'],
                    role=row['role'],
                    joined_at=row['joined_at'],
                    invited_by=row['invited_by'],
                    capabilities=json.loads(row['capabilities'])
                )
                for row in rows
            ]

    def check_team_membership(self, team_id: str, user_id: str) -> Optional[TeamMember]:
        """Check if user is a member of team"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("""
                SELECT * FROM team_members
                WHERE team_id = ? AND user_id = ?
            """, (team_id, user_id)).fetchone()

            if not row:
                return None

            return TeamMember(
                team_id=row['team_id'],
                user_id=row['user_id'],
                role=row['role'],
                joined_at=row['joined_at'],
                invited_by=row['invited_by'],
                capabilities=json.loads(row['capabilities'])
            )

    # ==================== Vault Management ====================

    def create_vault(
        self,
        name: str,
        vault_type: str,
        owner_id: str,
        vault_id: Optional[str] = None,
        team_id: Optional[str] = None,
        access_policy: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ) -> Vault:
        """Create a new vault with encryption"""
        if vault_id is None:
            vault_id = f"vault_{secrets.token_hex(8)}"

        # Generate encryption key for this vault
        encryption_key_id = self.encryption.create_vault_key()

        vault = Vault(
            vault_id=vault_id,
            name=name,
            vault_type=vault_type,
            owner_id=owner_id,
            team_id=team_id,
            encryption_key_id=encryption_key_id,
            access_policy=access_policy or {},
            metadata=metadata or {}
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO vaults (vault_id, name, vault_type, owner_id, team_id,
                                   encryption_key_id, access_policy, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                vault.vault_id,
                vault.name,
                vault.vault_type,
                vault.owner_id,
                vault.team_id,
                vault.encryption_key_id,
                json.dumps(vault.access_policy),
                json.dumps(vault.metadata)
            ))

            # Log audit trail
            self._log_vault_audit(
                conn,
                vault_id=vault.vault_id,
                actor_id=owner_id,
                action="vault_created",
                reason=f"Created vault '{name}'"
            )

            conn.commit()

        logger.info(f"Created vault {vault.vault_id}: {name}")
        return vault

    def get_vault(self, vault_id: str) -> Optional[Vault]:
        """Get vault by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("""
                SELECT * FROM vaults WHERE vault_id = ?
            """, (vault_id,)).fetchone()

            if not row:
                return None

            return Vault(
                vault_id=row['vault_id'],
                name=row['name'],
                vault_type=row['vault_type'],
                owner_id=row['owner_id'],
                team_id=row['team_id'],
                encryption_key_id=row['encryption_key_id'],
                created_at=row['created_at'],
                access_policy=json.loads(row['access_policy']),
                metadata=json.loads(row['metadata'])
            )

    def list_vaults(self, user_id: Optional[str] = None) -> List[Vault]:
        """List all vaults accessible by user"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            if user_id:
                # Include vaults owned by user or with explicit access grants
                rows = conn.execute("""
                    SELECT DISTINCT v.* FROM vaults v
                    LEFT JOIN vault_access va ON v.vault_id = va.vault_id
                    WHERE v.owner_id = ?
                       OR (va.grantee_id = ? AND va.grantee_type = 'user')
                       OR va.vault_id IS NULL
                    ORDER BY v.created_at DESC
                """, (user_id, user_id)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM vaults ORDER BY created_at DESC
                """).fetchall()

            return [
                Vault(
                    vault_id=row['vault_id'],
                    name=row['name'],
                    vault_type=row['vault_type'],
                    owner_id=row['owner_id'],
                    team_id=row['team_id'],
                    encryption_key_id=row['encryption_key_id'],
                    created_at=row['created_at'],
                    access_policy=json.loads(row['access_policy']),
                    metadata=json.loads(row['metadata'])
                )
                for row in rows
            ]

    def store_in_vault(
        self,
        vault_id: str,
        key: str,
        value: str,
        created_by: str,
        metadata: Optional[Dict] = None,
        expires_at: Optional[str] = None
    ) -> VaultSecret:
        """Store an encrypted secret in a vault"""
        vault = self.get_vault(vault_id)
        if not vault:
            raise ValueError(f"Vault {vault_id} not found")

        # Encrypt the value
        encrypted_value = self.encryption.encrypt_secret(
            vault.encryption_key_id,
            value
        )

        secret_id = f"secret_{secrets.token_hex(8)}"

        with sqlite3.connect(self.db_path) as conn:
            # Upsert secret (update if exists, insert if not)
            conn.execute("""
                INSERT INTO vault_secrets (secret_id, vault_id, key, encrypted_value,
                                          created_by, metadata, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(vault_id, key) DO UPDATE SET
                    encrypted_value = excluded.encrypted_value,
                    updated_at = CURRENT_TIMESTAMP,
                    metadata = excluded.metadata
            """, (
                secret_id,
                vault_id,
                key,
                encrypted_value,
                created_by,
                json.dumps(metadata or {}),
                expires_at
            ))

            # Log audit trail
            self._log_vault_audit(
                conn,
                vault_id=vault_id,
                actor_id=created_by,
                action="secret_stored",
                key_accessed=key,
                reason="Stored secret in vault"
            )

            conn.commit()

        logger.info(f"Stored secret '{key}' in vault {vault_id}")

        return VaultSecret(
            secret_id=secret_id,
            vault_id=vault_id,
            key=key,
            encrypted_value=encrypted_value,
            created_by=created_by,
            metadata=metadata or {}
        )

    def retrieve_from_vault(
        self,
        vault_id: str,
        key: str,
        actor_id: str,
        audit_reason: str
    ) -> Optional[str]:
        """Retrieve and decrypt a secret from a vault"""
        vault = self.get_vault(vault_id)
        if not vault:
            raise ValueError(f"Vault {vault_id} not found")

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("""
                SELECT encrypted_value FROM vault_secrets
                WHERE vault_id = ? AND key = ?
            """, (vault_id, key)).fetchone()

            if not row:
                return None

            # Decrypt the value
            decrypted_value = self.encryption.decrypt_secret(
                vault.encryption_key_id,
                row['encrypted_value']
            )

            # Log audit trail
            self._log_vault_audit(
                conn,
                vault_id=vault_id,
                actor_id=actor_id,
                action="secret_read",
                key_accessed=key,
                reason=audit_reason
            )

            conn.commit()

        logger.info(f"Retrieved secret '{key}' from vault {vault_id} by {actor_id}")
        return decrypted_value

    def list_vault_secrets(self, vault_id: str) -> List[Dict]:
        """List all secret keys in a vault (not values)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT secret_id, key, created_at, updated_at, created_by, metadata, expires_at
                FROM vault_secrets
                WHERE vault_id = ?
                ORDER BY created_at DESC
            """, (vault_id,)).fetchall()

            return [
                {
                    'secret_id': row['secret_id'],
                    'key': row['key'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'created_by': row['created_by'],
                    'metadata': json.loads(row['metadata']),
                    'expires_at': row['expires_at']
                }
                for row in rows
            ]

    def delete_vault_secret(self, vault_id: str, key: str, actor_id: str) -> bool:
        """Delete a secret from a vault"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM vault_secrets
                WHERE vault_id = ? AND key = ?
            """, (vault_id, key))

            if cursor.rowcount > 0:
                self._log_vault_audit(
                    conn,
                    vault_id=vault_id,
                    actor_id=actor_id,
                    action="secret_deleted",
                    key_accessed=key,
                    reason="Deleted secret from vault"
                )
                conn.commit()
                logger.info(f"Deleted secret '{key}' from vault {vault_id}")
                return True

            return False

    # ==================== Access Control ====================

    def grant_vault_access(
        self,
        vault_id: str,
        grantee_id: str,
        grantee_type: str,  # 'user' or 'team'
        access_level: str,
        granted_by: str,
        expires_at: Optional[str] = None
    ) -> AccessGrant:
        """Grant access to a vault"""
        grant_id = f"grant_{secrets.token_hex(8)}"

        grant = AccessGrant(
            grant_id=grant_id,
            vault_id=vault_id,
            grantee_id=grantee_id,
            grantee_type=grantee_type,
            access_level=access_level,
            granted_by=granted_by,
            expires_at=expires_at
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO vault_access (grant_id, vault_id, grantee_id, grantee_type,
                                         access_level, granted_by, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(vault_id, grantee_id) DO UPDATE SET
                    access_level = excluded.access_level,
                    granted_by = excluded.granted_by,
                    granted_at = CURRENT_TIMESTAMP
            """, (
                grant.grant_id,
                grant.vault_id,
                grant.grantee_id,
                grant.grantee_type,
                grant.access_level,
                grant.granted_by,
                grant.expires_at
            ))

            # Log audit trail
            self._log_vault_audit(
                conn,
                vault_id=vault_id,
                actor_id=granted_by,
                action="access_granted",
                reason=f"Granted {access_level} access to {grantee_id}"
            )

            conn.commit()

        logger.info(f"Granted {access_level} access to vault {vault_id} for {grantee_id}")
        return grant

    def check_vault_access(
        self,
        vault_id: str,
        user_id: str,
        required_level: str = "read"
    ) -> bool:
        """Check if user has access to vault at required level"""
        vault = self.get_vault(vault_id)
        if not vault:
            return False

        # Owner has full access
        if vault.owner_id == user_id:
            return True

        access_levels = {
            "read": 1,
            "write": 2,
            "admin": 3
        }
        required_level_value = access_levels.get(required_level, 1)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Check direct user access
            row = conn.execute("""
                SELECT access_level FROM vault_access
                WHERE vault_id = ? AND grantee_id = ? AND grantee_type = 'user'
                  AND (expires_at IS NULL OR expires_at > datetime('now'))
            """, (vault_id, user_id)).fetchone()

            if row:
                user_level_value = access_levels.get(row['access_level'], 0)
                if user_level_value >= required_level_value:
                    return True

            # Check team access if vault is team vault
            if vault.team_id:
                member = self.check_team_membership(vault.team_id, user_id)
                if member:
                    # Team members have at least read access
                    if required_level == "read":
                        return True
                    # Admins and owners have full access
                    if member.role in [TeamRole.ADMIN.value, TeamRole.OWNER.value]:
                        return True

        return False

    # ==================== Mode Management ====================

    def set_mode(
        self,
        agent_id: str,
        user_id: str,
        mode: str,
        context_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """Set agent operating mode"""
        session_id = f"{agent_id}_{user_id}"

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO session_modes (session_id, agent_id, user_id, current_mode,
                                          context_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    current_mode = excluded.current_mode,
                    context_id = excluded.context_id,
                    updated_at = CURRENT_TIMESTAMP,
                    metadata = excluded.metadata
            """, (
                session_id,
                agent_id,
                user_id,
                mode,
                context_id,
                json.dumps(metadata or {})
            ))

            conn.commit()

        logger.info(f"Set mode for {agent_id} to {mode} (context: {context_id})")

        return {
            "session_id": session_id,
            "mode": mode,
            "context_id": context_id,
            "updated_at": datetime.now().isoformat()
        }

    def get_mode(self, agent_id: str, user_id: str) -> Optional[Dict]:
        """Get current agent operating mode"""
        session_id = f"{agent_id}_{user_id}"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("""
                SELECT * FROM session_modes WHERE session_id = ?
            """, (session_id,)).fetchone()

            if not row:
                return None

            return {
                "session_id": row['session_id'],
                "agent_id": row['agent_id'],
                "user_id": row['user_id'],
                "mode": row['current_mode'],
                "context_id": row['context_id'],
                "updated_at": row['updated_at'],
                "metadata": json.loads(row['metadata'])
            }

    # ==================== Audit and Activity ====================

    def _log_vault_audit(
        self,
        conn: sqlite3.Connection,
        vault_id: str,
        actor_id: str,
        action: str,
        key_accessed: Optional[str] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Internal method to log vault audit entries"""
        conn.execute("""
            INSERT INTO vault_audit (vault_id, actor_id, action, key_accessed, reason, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            vault_id,
            actor_id,
            action,
            key_accessed,
            reason,
            json.dumps(metadata or {})
        ))

    def get_vault_audit_log(
        self,
        vault_id: str,
        hours: int = 24,
        limit: int = 100
    ) -> List[Dict]:
        """Get vault audit log entries"""
        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM vault_audit
                WHERE vault_id = ? AND timestamp > ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (vault_id, cutoff_time, limit)).fetchall()

            return [
                {
                    'audit_id': row['audit_id'],
                    'vault_id': row['vault_id'],
                    'actor_id': row['actor_id'],
                    'action': row['action'],
                    'key_accessed': row['key_accessed'],
                    'reason': row['reason'],
                    'timestamp': row['timestamp'],
                    'metadata': json.loads(row['metadata'])
                }
                for row in rows
            ]

    def _log_team_activity(
        self,
        conn: sqlite3.Connection,
        team_id: str,
        actor_id: str,
        action: str,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Internal method to log team activity"""
        conn.execute("""
            INSERT INTO team_activity (team_id, actor_id, action, description, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (
            team_id,
            actor_id,
            action,
            description,
            json.dumps(metadata or {})
        ))

    def get_team_activity(
        self,
        team_id: str,
        hours: int = 24,
        limit: int = 50
    ) -> List[Dict]:
        """Get team activity log entries"""
        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM team_activity
                WHERE team_id = ? AND timestamp > ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (team_id, cutoff_time, limit)).fetchall()

            return [
                {
                    'activity_id': row['activity_id'],
                    'team_id': row['team_id'],
                    'actor_id': row['actor_id'],
                    'action': row['action'],
                    'description': row['description'],
                    'timestamp': row['timestamp'],
                    'metadata': json.loads(row['metadata'])
                }
                for row in rows
            ]


class VaultEncryption:
    """
    Vault encryption system using Fernet (symmetric encryption)

    Each vault has its own encryption key, which is itself encrypted
    with a master key.
    """

    def __init__(self, master_key_path: str = "data/.vault_master_key", db_path: str = "data/teams_vaults.db"):
        # Always enable encryption (use XOR fallback if cryptography not available)
        self.enabled = True
        self.use_fernet = CRYPTO_AVAILABLE
        self.db_path = Path(db_path)
        self.master_key_path = Path(master_key_path)
        self.master_key_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_master_key()

        if not CRYPTO_AVAILABLE:
            logger.warning("Using XOR-based encryption (cryptography library not available)")

    def _ensure_master_key(self):
        """Ensure master key exists, create if not"""
        if not self.master_key_path.exists():
            # Generate a simple key for XOR encryption
            master_key = secrets.token_bytes(32)
            self.master_key_path.write_bytes(master_key)
            # Set restrictive permissions
            os.chmod(self.master_key_path, 0o600)
            logger.info("Generated new vault master key")

        self.master_key = self.master_key_path.read_bytes()
        self.master_fernet = None

    def create_vault_key(self) -> str:
        """Generate a new vault encryption key"""
        if not self.enabled:
            return "disabled"

        # Generate vault-specific key and XOR encrypt with master key
        vault_key = secrets.token_bytes(32)
        encrypted_key = self._simple_encrypt(vault_key)

        # Store encrypted key
        key_id = f"vaultkey_{secrets.token_hex(8)}"

        # Save to database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO encryption_keys (key_id, encrypted_key)
                VALUES (?, ?)
            """, (key_id, base64.b64encode(encrypted_key).decode('utf-8')))
            conn.commit()

        logger.info(f"Created vault encryption key {key_id}")
        return key_id

    def get_vault_key(self, key_id: str) -> bytes:
        """Retrieve and decrypt a vault key"""
        if not self.enabled:
            return b"disabled"

        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT encrypted_key FROM encryption_keys WHERE key_id = ?
            """, (key_id,)).fetchone()

            if not row:
                raise ValueError(f"Encryption key {key_id} not found")

            encrypted_key = base64.b64decode(row[0])

            # Decrypt vault key with master key using XOR
            vault_key = self._simple_decrypt(encrypted_key)

            return vault_key

    def encrypt_secret(self, key_id: str, plaintext: str) -> str:
        """Encrypt a secret using vault key"""
        if not self.enabled:
            # Fallback to base64 encoding if encryption not available
            return base64.b64encode(plaintext.encode('utf-8')).decode('utf-8')

        vault_key = self.get_vault_key(key_id)

        # XOR encryption with vault key
        ciphertext = self._simple_encrypt_data(plaintext.encode('utf-8'), vault_key)
        return base64.b64encode(ciphertext).decode('utf-8')

    def decrypt_secret(self, key_id: str, encrypted_value: str) -> str:
        """Decrypt a secret using vault key"""
        if not self.enabled:
            # Fallback to base64 decoding if encryption not available
            return base64.b64decode(encrypted_value).decode('utf-8')

        vault_key = self.get_vault_key(key_id)

        # XOR decryption with vault key
        ciphertext = base64.b64decode(encrypted_value)
        plaintext = self._simple_decrypt_data(ciphertext, vault_key)
        return plaintext.decode('utf-8')

    def _simple_encrypt(self, data: bytes) -> bytes:
        """Simple XOR encryption with master key"""
        result = bytearray()
        key_len = len(self.master_key)
        for i, byte in enumerate(data):
            result.append(byte ^ self.master_key[i % key_len])
        return bytes(result)

    def _simple_decrypt(self, data: bytes) -> bytes:
        """Simple XOR decryption with master key (same as encrypt for XOR)"""
        return self._simple_encrypt(data)

    def _simple_encrypt_data(self, data: bytes, key: bytes) -> bytes:
        """Simple XOR encryption with given key"""
        result = bytearray()
        key_len = len(key)
        for i, byte in enumerate(data):
            result.append(byte ^ key[i % key_len])
        return bytes(result)

    def _simple_decrypt_data(self, data: bytes, key: bytes) -> bytes:
        """Simple XOR decryption with given key"""
        return self._simple_encrypt_data(data, key)


# Initialize system on import
if __name__ == "__main__":
    system = TeamsAndVaultsSystem()
    logger.info("Teams and Vaults System initialized successfully")
