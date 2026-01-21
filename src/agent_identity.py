"""
Agent Identity System for hAIveMind

Implements Tailscale-style agent identity with:
- Cryptographic identity (Ed25519 for signing, X25519 for key exchange)
- Pre-auth keys for automated registration
- Machine binding to prevent identity theft
- Firebase integration for token management
"""

import os
import hashlib
import secrets
import sqlite3
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import base64

logger = logging.getLogger(__name__)

# Try to import cryptography libraries
try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logger.warning("cryptography library not available. Install with: pip install cryptography")

# Import Firebase auth
from .firebase_auth import get_firebase_auth, AgentClaims


class AgentStatus(Enum):
    """Agent lifecycle states (Tailscale-style)"""
    PENDING = "pending"       # Awaiting approval
    APPROVED = "approved"     # Approved but not yet active
    ACTIVE = "active"         # Fully operational
    REVOKED = "revoked"       # Access revoked
    SUSPENDED = "suspended"   # Temporarily suspended


@dataclass
class AgentKeyPair:
    """Cryptographic key pair for an agent"""
    ed25519_private: bytes      # Signing key (private)
    ed25519_public: bytes       # Signing key (public)
    x25519_private: bytes       # Key exchange (private)
    x25519_public: bytes        # Key exchange (public)
    fingerprint: str            # SHA256 fingerprint of public keys

    @property
    def private_key_ed25519(self) -> str:
        """Get base64-encoded Ed25519 private key"""
        return base64.b64encode(self.ed25519_private).decode('utf-8')

    @property
    def private_key_x25519(self) -> str:
        """Get base64-encoded X25519 private key"""
        return base64.b64encode(self.x25519_private).decode('utf-8')


@dataclass
class AgentIdentity:
    """Full agent identity record"""
    identity_id: str
    agent_id: str
    firebase_uid: Optional[str]
    machine_id: str
    public_key_ed25519: str     # Base64 encoded
    public_key_x25519: str      # Base64 encoded
    key_fingerprint: str
    status: AgentStatus
    machine_binding_hash: str
    approved_by: Optional[str]
    approved_at: Optional[str]
    created_at: str
    tags: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidentiality_max: str = "normal"
    agent_type: str = "general"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "identity_id": self.identity_id,
            "agent_id": self.agent_id,
            "firebase_uid": self.firebase_uid,
            "machine_id": self.machine_id,
            "public_key_ed25519": self.public_key_ed25519,
            "public_key_x25519": self.public_key_x25519,
            "key_fingerprint": self.key_fingerprint,
            "status": self.status.value if isinstance(self.status, AgentStatus) else self.status,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "created_at": self.created_at,
            "tags": self.tags,
            "capabilities": self.capabilities,
            "confidentiality_max": self.confidentiality_max,
            "agent_type": self.agent_type
        }


@dataclass
class PreAuthKey:
    """Pre-authorization key for automated agent registration (Tailscale-style)"""
    key_id: str
    key_prefix: str             # First 8 chars for identification
    created_by: str
    created_at: str
    expires_at: Optional[str]
    max_uses: Optional[int]
    current_uses: int
    tags: List[str]
    capabilities: List[str]
    machine_group: Optional[str]
    ephemeral: bool             # Agent disappears when inactive
    reusable: bool              # Can be used multiple times
    pre_approved: bool          # Skip approval queue
    revoked: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "key_id": self.key_id,
            "key_prefix": self.key_prefix,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "max_uses": self.max_uses,
            "current_uses": self.current_uses,
            "tags": self.tags,
            "capabilities": self.capabilities,
            "machine_group": self.machine_group,
            "ephemeral": self.ephemeral,
            "reusable": self.reusable,
            "pre_approved": self.pre_approved,
            "revoked": self.revoked
        }


class AgentIdentitySystem:
    """
    Agent Identity and Authentication System

    Combines Tailscale-style pre-auth keys and device approval
    with 1Password-style cryptographic identity and Firebase
    token management.
    """

    def __init__(self, db_path: str = "data/agent_identity.db"):
        """Initialize the agent identity system"""
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        self.firebase = get_firebase_auth()

    def _init_database(self):
        """Initialize SQLite database with schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Agent identities table (linked to Firebase)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_identities (
                identity_id TEXT PRIMARY KEY,
                agent_id TEXT UNIQUE NOT NULL,
                firebase_uid TEXT UNIQUE,
                machine_id TEXT NOT NULL,
                public_key_ed25519 TEXT NOT NULL,
                public_key_x25519 TEXT NOT NULL,
                key_fingerprint TEXT UNIQUE NOT NULL,
                status TEXT CHECK(status IN ('pending', 'approved', 'active', 'revoked', 'suspended')) DEFAULT 'pending',
                machine_binding_hash TEXT NOT NULL,
                approved_by TEXT,
                approved_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}'
            )
        """)

        # Agent tags (Tailscale-style)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_tags (
                tag_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                tag_name TEXT NOT NULL,
                granted_by TEXT NOT NULL,
                granted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT,
                UNIQUE(agent_id, tag_name),
                FOREIGN KEY (agent_id) REFERENCES agent_identities(agent_id) ON DELETE CASCADE
            )
        """)

        # Agent capabilities
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_capabilities (
                capability_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                capability_name TEXT NOT NULL,
                granted_by TEXT NOT NULL,
                granted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT,
                UNIQUE(agent_id, capability_name),
                FOREIGN KEY (agent_id) REFERENCES agent_identities(agent_id) ON DELETE CASCADE
            )
        """)

        # Pre-auth keys (Tailscale-style)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pre_auth_keys (
                key_id TEXT PRIMARY KEY,
                key_hash TEXT UNIQUE NOT NULL,
                key_prefix TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT,
                max_uses INTEGER DEFAULT 1,
                current_uses INTEGER DEFAULT 0,
                tags TEXT DEFAULT '[]',
                capabilities TEXT DEFAULT '[]',
                machine_group TEXT,
                ephemeral BOOLEAN DEFAULT FALSE,
                reusable BOOLEAN DEFAULT FALSE,
                pre_approved BOOLEAN DEFAULT FALSE,
                revoked BOOLEAN DEFAULT FALSE,
                revoked_at TEXT,
                revoked_by TEXT,
                metadata TEXT DEFAULT '{}'
            )
        """)

        # Agent sessions (token tracking)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_sessions (
                session_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                token_hash TEXT UNIQUE NOT NULL,
                token_prefix TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT NOT NULL,
                last_activity TEXT,
                ip_address TEXT,
                machine_id TEXT,
                revoked BOOLEAN DEFAULT FALSE,
                revoked_at TEXT,
                revoked_reason TEXT,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (agent_id) REFERENCES agent_identities(agent_id) ON DELETE CASCADE
            )
        """)

        # Access grants (ACL rules)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS access_grants (
                grant_id TEXT PRIMARY KEY,
                grant_name TEXT UNIQUE NOT NULL,
                description TEXT,
                priority INTEGER DEFAULT 100,
                enabled BOOLEAN DEFAULT TRUE,
                src_agents TEXT DEFAULT '[]',
                src_tags TEXT DEFAULT '[]',
                src_roles TEXT DEFAULT '[]',
                src_teams TEXT DEFAULT '[]',
                dst_vaults TEXT DEFAULT '[]',
                dst_memories TEXT DEFAULT '[]',
                dst_agents TEXT DEFAULT '[]',
                dst_resources TEXT DEFAULT '[]',
                permissions TEXT NOT NULL,
                conditions TEXT DEFAULT '{}',
                created_by TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT,
                expires_at TEXT,
                metadata TEXT DEFAULT '{}'
            )
        """)

        # Token revocation list
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS token_revocations (
                revocation_id TEXT PRIMARY KEY,
                token_hash TEXT,
                agent_id TEXT,
                revoked_at TEXT DEFAULT CURRENT_TIMESTAMP,
                revoked_by TEXT NOT NULL,
                reason TEXT,
                expires_at TEXT NOT NULL
            )
        """)

        # Agent approval queue
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_approvals (
                approval_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                identity_id TEXT NOT NULL,
                requested_at TEXT DEFAULT CURRENT_TIMESTAMP,
                machine_id TEXT NOT NULL,
                pre_auth_key_id TEXT,
                requested_tags TEXT DEFAULT '[]',
                requested_capabilities TEXT DEFAULT '[]',
                status TEXT CHECK(status IN ('pending', 'approved', 'rejected')) DEFAULT 'pending',
                reviewed_by TEXT,
                reviewed_at TEXT,
                review_notes TEXT,
                auto_approved BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (identity_id) REFERENCES agent_identities(identity_id)
            )
        """)

        # Comprehensive audit log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_audit_log (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                agent_id TEXT,
                session_id TEXT,
                action TEXT NOT NULL,
                resource_type TEXT,
                resource_id TEXT,
                permission_used TEXT,
                grant_matched TEXT,
                result TEXT CHECK(result IN ('success', 'denied', 'error')),
                denial_reason TEXT,
                ip_address TEXT,
                machine_id TEXT,
                request_metadata TEXT DEFAULT '{}',
                response_metadata TEXT DEFAULT '{}'
            )
        """)

        # Vault access shares (zero-knowledge)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vault_access_shares (
                share_id TEXT PRIMARY KEY,
                vault_id TEXT NOT NULL,
                recipient_agent_id TEXT NOT NULL,
                recipient_firebase_uid TEXT,
                encrypted_vault_key TEXT NOT NULL,
                access_level TEXT CHECK(access_level IN ('read', 'write', 'admin')) DEFAULT 'read',
                granted_by TEXT NOT NULL,
                granted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT,
                revoked BOOLEAN DEFAULT FALSE,
                UNIQUE(vault_id, recipient_agent_id)
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_identity_machine ON agent_identities(machine_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_identity_status ON agent_identities(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_identity_fingerprint ON agent_identities(key_fingerprint)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_tags_name ON agent_tags(tag_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_preauth_expires ON pre_auth_keys(expires_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_agent ON agent_sessions(agent_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_expires ON agent_sessions(expires_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_grants_priority ON access_grants(priority)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_revocations_token ON token_revocations(token_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_revocations_agent ON token_revocations(agent_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_approvals_status ON agent_approvals(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON agent_audit_log(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_agent ON agent_audit_log(agent_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON agent_audit_log(action)")

        conn.commit()
        conn.close()
        logger.info(f"Agent identity database initialized at {self.db_path}")

    # ==================== Key Generation ====================

    def generate_key_pair(self) -> Optional[AgentKeyPair]:
        """
        Generate Ed25519 (signing) and X25519 (key exchange) key pairs

        Returns:
            AgentKeyPair with all key material
        """
        if not CRYPTO_AVAILABLE:
            logger.error("Cryptography library not available")
            return None

        try:
            # Generate Ed25519 key pair (for signing)
            ed25519_private = Ed25519PrivateKey.generate()
            ed25519_public = ed25519_private.public_key()

            # Generate X25519 key pair (for key exchange)
            x25519_private = X25519PrivateKey.generate()
            x25519_public = x25519_private.public_key()

            # Serialize keys
            ed25519_private_bytes = ed25519_private.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption()
            )
            ed25519_public_bytes = ed25519_public.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            x25519_private_bytes = x25519_private.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption()
            )
            x25519_public_bytes = x25519_public.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )

            # Compute fingerprint (SHA256 of concatenated public keys)
            fingerprint_input = ed25519_public_bytes + x25519_public_bytes
            fingerprint = hashlib.sha256(fingerprint_input).hexdigest()

            return AgentKeyPair(
                ed25519_private=ed25519_private_bytes,
                ed25519_public=ed25519_public_bytes,
                x25519_private=x25519_private_bytes,
                x25519_public=x25519_public_bytes,
                fingerprint=fingerprint
            )

        except Exception as e:
            logger.error(f"Failed to generate key pair: {e}")
            return None

    def compute_machine_binding(self, machine_id: str, public_key_fingerprint: str) -> str:
        """
        Compute machine binding hash to prevent key migration

        This ties the agent identity to a specific machine.
        """
        binding_input = f"{machine_id}:{public_key_fingerprint}"
        return hashlib.sha256(binding_input.encode()).hexdigest()

    # ==================== Pre-Auth Keys ====================

    def create_pre_auth_key(
        self,
        created_by: str,
        expires_hours: int = 24,
        max_uses: int = 1,
        tags: Optional[List[str]] = None,
        capabilities: Optional[List[str]] = None,
        machine_group: Optional[str] = None,
        ephemeral: bool = False,
        reusable: bool = False,
        pre_approved: bool = False,
    ) -> Tuple[Optional[str], Optional[PreAuthKey]]:
        """
        Create a pre-authorization key (Tailscale-style)

        Args:
            created_by: Admin who created the key
            expires_hours: Hours until key expires
            max_uses: Maximum number of uses (None for unlimited)
            tags: Tags to assign to registering agents
            capabilities: Capabilities to grant
            machine_group: Restrict to specific machine group
            ephemeral: If True, agent is removed when inactive
            reusable: If True, key can be used multiple times
            pre_approved: If True, skip approval queue

        Returns:
            Tuple of (raw key, PreAuthKey record) or (None, None) on error
        """
        try:
            # Generate secure random key
            raw_key = f"pak_{secrets.token_urlsafe(32)}"
            key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
            key_prefix = raw_key[:12]
            key_id = f"pak_{secrets.token_hex(8)}"

            expires_at = (datetime.utcnow() + timedelta(hours=expires_hours)).isoformat() if expires_hours else None

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO pre_auth_keys (
                    key_id, key_hash, key_prefix, created_by, expires_at,
                    max_uses, tags, capabilities, machine_group,
                    ephemeral, reusable, pre_approved
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                key_id, key_hash, key_prefix, created_by, expires_at,
                max_uses, json.dumps(tags or []), json.dumps(capabilities or []),
                machine_group, ephemeral, reusable, pre_approved
            ))

            conn.commit()
            conn.close()

            pak = PreAuthKey(
                key_id=key_id,
                key_prefix=key_prefix,
                created_by=created_by,
                created_at=datetime.utcnow().isoformat(),
                expires_at=expires_at,
                max_uses=max_uses,
                current_uses=0,
                tags=tags or [],
                capabilities=capabilities or [],
                machine_group=machine_group,
                ephemeral=ephemeral,
                reusable=reusable,
                pre_approved=pre_approved,
                revoked=False
            )

            logger.info(f"Created pre-auth key {key_prefix}... by {created_by}")
            return raw_key, pak

        except Exception as e:
            logger.error(f"Failed to create pre-auth key: {e}")
            return None, None

    def validate_pre_auth_key(self, raw_key: str) -> Optional[PreAuthKey]:
        """
        Validate a pre-auth key

        Returns:
            PreAuthKey if valid, None otherwise
        """
        try:
            key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT key_id, key_prefix, created_by, created_at, expires_at,
                       max_uses, current_uses, tags, capabilities, machine_group,
                       ephemeral, reusable, pre_approved, revoked
                FROM pre_auth_keys
                WHERE key_hash = ?
            """, (key_hash,))

            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            pak = PreAuthKey(
                key_id=row[0],
                key_prefix=row[1],
                created_by=row[2],
                created_at=row[3],
                expires_at=row[4],
                max_uses=row[5],
                current_uses=row[6],
                tags=json.loads(row[7]) if row[7] else [],
                capabilities=json.loads(row[8]) if row[8] else [],
                machine_group=row[9],
                ephemeral=bool(row[10]),
                reusable=bool(row[11]),
                pre_approved=bool(row[12]),
                revoked=bool(row[13])
            )

            # Check validity
            if pak.revoked:
                logger.warning(f"Pre-auth key {pak.key_prefix}... is revoked")
                return None

            if pak.expires_at and datetime.fromisoformat(pak.expires_at) < datetime.utcnow():
                logger.warning(f"Pre-auth key {pak.key_prefix}... has expired")
                return None

            if pak.max_uses and pak.current_uses >= pak.max_uses:
                logger.warning(f"Pre-auth key {pak.key_prefix}... has exceeded max uses")
                return None

            return pak

        except Exception as e:
            logger.error(f"Failed to validate pre-auth key: {e}")
            return None

    def use_pre_auth_key(self, raw_key: str) -> bool:
        """Increment the use count of a pre-auth key"""
        try:
            key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE pre_auth_keys
                SET current_uses = current_uses + 1
                WHERE key_hash = ?
            """, (key_hash,))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Failed to use pre-auth key: {e}")
            return False

    def list_pre_auth_keys(
        self,
        include_revoked: bool = False,
        include_expired: bool = False,
        include_used: bool = False
    ) -> List[PreAuthKey]:
        """List all pre-auth keys with optional filtering"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = """
                SELECT key_id, key_prefix, created_by, created_at, expires_at,
                       max_uses, current_uses, tags, capabilities, machine_group,
                       ephemeral, reusable, pre_approved, revoked
                FROM pre_auth_keys
                WHERE 1=1
            """
            if not include_revoked:
                query += " AND revoked = FALSE"
            if not include_expired:
                query += " AND (expires_at IS NULL OR expires_at > datetime('now'))"
            if not include_used:
                query += " AND (max_uses IS NULL OR current_uses < max_uses)"

            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()

            return [PreAuthKey(
                key_id=row[0],
                key_prefix=row[1],
                created_by=row[2],
                created_at=row[3],
                expires_at=row[4],
                max_uses=row[5],
                current_uses=row[6],
                tags=json.loads(row[7]) if row[7] else [],
                capabilities=json.loads(row[8]) if row[8] else [],
                machine_group=row[9],
                ephemeral=bool(row[10]),
                reusable=bool(row[11]),
                pre_approved=bool(row[12]),
                revoked=bool(row[13])
            ) for row in rows]

        except Exception as e:
            logger.error(f"Failed to list pre-auth keys: {e}")
            return []

    def revoke_pre_auth_key(self, key_id: str, revoked_by: str) -> bool:
        """Revoke a pre-auth key"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE pre_auth_keys
                SET revoked = TRUE, revoked_at = ?, revoked_by = ?
                WHERE key_id = ?
            """, (datetime.utcnow().isoformat(), revoked_by, key_id))

            conn.commit()
            conn.close()
            logger.info(f"Revoked pre-auth key {key_id} by {revoked_by}")
            return True

        except Exception as e:
            logger.error(f"Failed to revoke pre-auth key: {e}")
            return False

    # ==================== Agent Registration ====================

    def register_agent(
        self,
        machine_id: str,
        agent_type: str = "general",
        pre_auth_key: Optional[str] = None,
        requested_tags: Optional[List[str]] = None,
        requested_capabilities: Optional[List[str]] = None,
    ) -> Tuple[Optional[AgentIdentity], Optional[AgentKeyPair], Optional[str]]:
        """
        Register a new agent identity

        Args:
            machine_id: Machine identifier (hostname or Tailscale ID)
            agent_type: Type of agent (elasticsearch, orchestrator, etc.)
            pre_auth_key: Optional pre-auth key for automatic approval
            requested_tags: Tags to request
            requested_capabilities: Capabilities to request

        Returns:
            Tuple of (AgentIdentity, AgentKeyPair, firebase_token) or (None, None, None)
        """
        try:
            # Generate cryptographic identity
            key_pair = self.generate_key_pair()
            if not key_pair:
                logger.error("Failed to generate key pair")
                return None, None, None

            # Create agent ID
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            agent_id = f"{machine_id}-{agent_type}-{timestamp}"
            identity_id = f"id_{secrets.token_hex(16)}"

            # Compute machine binding
            machine_binding_hash = self.compute_machine_binding(machine_id, key_pair.fingerprint)

            # Validate pre-auth key if provided
            pak = None
            if pre_auth_key:
                pak = self.validate_pre_auth_key(pre_auth_key)
                if not pak:
                    logger.warning(f"Invalid pre-auth key for agent registration")
                    return None, None, None

            # Determine initial status
            if pak and pak.pre_approved:
                status = AgentStatus.ACTIVE
            else:
                status = AgentStatus.PENDING

            # Apply tags and capabilities from pre-auth key
            tags = list(set((requested_tags or []) + (pak.tags if pak else [])))
            capabilities = list(set((requested_capabilities or []) + (pak.capabilities if pak else [])))

            # Create Firebase user
            firebase_uid = None
            firebase_token = None
            if self.firebase.is_available():
                firebase_uid = self.firebase.create_agent_user(agent_id, f"Agent: {agent_id}")
                if firebase_uid:
                    # Set custom claims
                    claims = AgentClaims(
                        agent_type=agent_type,
                        machine_id=machine_id,
                        tags=tags,
                        capabilities=capabilities,
                        confidentiality_max="normal",
                        approved_at=datetime.utcnow().isoformat() if status == AgentStatus.ACTIVE else None
                    )
                    self.firebase.set_agent_claims(agent_id, claims)

                    # Mint token
                    firebase_token = self.firebase.mint_agent_token(agent_id, claims.to_dict())

            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO agent_identities (
                    identity_id, agent_id, firebase_uid, machine_id,
                    public_key_ed25519, public_key_x25519, key_fingerprint,
                    status, machine_binding_hash, approved_by, approved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                identity_id, agent_id, firebase_uid, machine_id,
                base64.b64encode(key_pair.ed25519_public).decode(),
                base64.b64encode(key_pair.x25519_public).decode(),
                key_pair.fingerprint,
                status.value,
                machine_binding_hash,
                "pre-auth-key" if pak and pak.pre_approved else None,
                datetime.utcnow().isoformat() if status == AgentStatus.ACTIVE else None
            ))

            # Add tags
            for tag in tags:
                tag_id = f"tag_{secrets.token_hex(8)}"
                cursor.execute("""
                    INSERT OR IGNORE INTO agent_tags (tag_id, agent_id, tag_name, granted_by)
                    VALUES (?, ?, ?, ?)
                """, (tag_id, agent_id, tag, "registration"))

            # Add capabilities
            for cap in capabilities:
                cap_id = f"cap_{secrets.token_hex(8)}"
                cursor.execute("""
                    INSERT OR IGNORE INTO agent_capabilities (capability_id, agent_id, capability_name, granted_by)
                    VALUES (?, ?, ?, ?)
                """, (cap_id, agent_id, cap, "registration"))

            # Create approval request if pending
            if status == AgentStatus.PENDING:
                approval_id = f"apr_{secrets.token_hex(8)}"
                cursor.execute("""
                    INSERT INTO agent_approvals (
                        approval_id, agent_id, identity_id, machine_id,
                        pre_auth_key_id, requested_tags, requested_capabilities, auto_approved
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    approval_id, agent_id, identity_id, machine_id,
                    pak.key_id if pak else None,
                    json.dumps(tags), json.dumps(capabilities), False
                ))

            # Use pre-auth key if provided
            if pak:
                self.use_pre_auth_key(pre_auth_key)

            conn.commit()
            conn.close()

            identity = AgentIdentity(
                identity_id=identity_id,
                agent_id=agent_id,
                firebase_uid=firebase_uid,
                machine_id=machine_id,
                public_key_ed25519=base64.b64encode(key_pair.ed25519_public).decode(),
                public_key_x25519=base64.b64encode(key_pair.x25519_public).decode(),
                key_fingerprint=key_pair.fingerprint,
                status=status,
                machine_binding_hash=machine_binding_hash,
                approved_by="pre-auth-key" if pak and pak.pre_approved else None,
                approved_at=datetime.utcnow().isoformat() if status == AgentStatus.ACTIVE else None,
                created_at=datetime.utcnow().isoformat(),
                tags=tags,
                capabilities=capabilities
            )

            logger.info(f"Registered agent {agent_id} with status {status.value}")
            return identity, key_pair, firebase_token

        except Exception as e:
            logger.error(f"Failed to register agent: {e}")
            return None, None, None

    def get_agent(self, agent_id: str) -> Optional[AgentIdentity]:
        """Get an agent by ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT identity_id, agent_id, firebase_uid, machine_id,
                       public_key_ed25519, public_key_x25519, key_fingerprint,
                       status, machine_binding_hash, approved_by, approved_at,
                       created_at, metadata
                FROM agent_identities
                WHERE agent_id = ?
            """, (agent_id,))

            row = cursor.fetchone()
            if not row:
                conn.close()
                return None

            # Get tags
            cursor.execute("SELECT tag_name FROM agent_tags WHERE agent_id = ?", (agent_id,))
            tags = [r[0] for r in cursor.fetchall()]

            # Get capabilities
            cursor.execute("SELECT capability_name FROM agent_capabilities WHERE agent_id = ?", (agent_id,))
            capabilities = [r[0] for r in cursor.fetchall()]

            conn.close()

            return AgentIdentity(
                identity_id=row[0],
                agent_id=row[1],
                firebase_uid=row[2],
                machine_id=row[3],
                public_key_ed25519=row[4],
                public_key_x25519=row[5],
                key_fingerprint=row[6],
                status=AgentStatus(row[7]),
                machine_binding_hash=row[8],
                approved_by=row[9],
                approved_at=row[10],
                created_at=row[11],
                tags=tags,
                capabilities=capabilities,
                metadata=json.loads(row[12]) if row[12] else {}
            )

        except Exception as e:
            logger.error(f"Failed to get agent {agent_id}: {e}")
            return None

    def get_agent_by_firebase_uid(self, firebase_uid: str) -> Optional[AgentIdentity]:
        """Get an agent by their Firebase UID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT agent_id FROM agent_identities WHERE firebase_uid = ?",
                (firebase_uid,)
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                return self.get_agent(row[0])
            return None

        except Exception as e:
            logger.error(f"Failed to get agent by Firebase UID {firebase_uid}: {e}")
            return None

    def list_pending_agents(self) -> List[AgentIdentity]:
        """List all agents pending approval"""
        return self.list_agents(status_filter="pending")

    def list_agents(
        self,
        status_filter: Optional[str] = None,
        machine_filter: Optional[str] = None,
        limit: int = 100
    ) -> List[AgentIdentity]:
        """List all agents with optional filtering"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = "SELECT agent_id FROM agent_identities WHERE 1=1"
            params = []

            if status_filter:
                query += " AND status = ?"
                # Handle both string and enum
                status_val = status_filter.value if isinstance(status_filter, AgentStatus) else status_filter
                params.append(status_val)

            if machine_filter:
                query += " AND machine_id LIKE ?"
                params.append(f"%{machine_filter}%")

            query += f" LIMIT {limit}"

            cursor.execute(query, params)
            agent_ids = [r[0] for r in cursor.fetchall()]
            conn.close()

            return [self.get_agent(aid) for aid in agent_ids if self.get_agent(aid)]

        except Exception as e:
            logger.error(f"Failed to list agents: {e}")
            return []

    # ==================== Agent Approval ====================

    def approve_agent(
        self,
        agent_id: str,
        approved_by: str,
        tags_granted: Optional[List[str]] = None,
        capabilities_granted: Optional[List[str]] = None,
        notes: Optional[str] = None
    ) -> bool:
        """Approve a pending agent"""
        try:
            agent = self.get_agent(agent_id)
            if not agent:
                logger.error(f"Agent not found: {agent_id}")
                return False

            if agent.status != AgentStatus.PENDING:
                logger.warning(f"Agent {agent_id} is not pending approval")
                return False

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Update agent status
            cursor.execute("""
                UPDATE agent_identities
                SET status = ?, approved_by = ?, approved_at = ?
                WHERE agent_id = ?
            """, (AgentStatus.ACTIVE.value, approved_by, datetime.utcnow().isoformat(), agent_id))

            # Add granted tags
            if tags_granted:
                for tag in tags_granted:
                    tag_id = f"tag_{secrets.token_hex(8)}"
                    cursor.execute("""
                        INSERT OR IGNORE INTO agent_tags (tag_id, agent_id, tag_name, granted_by)
                        VALUES (?, ?, ?, ?)
                    """, (tag_id, agent_id, tag, approved_by))

            # Add granted capabilities
            if capabilities_granted:
                for cap in capabilities_granted:
                    cap_id = f"cap_{secrets.token_hex(8)}"
                    cursor.execute("""
                        INSERT OR IGNORE INTO agent_capabilities (capability_id, agent_id, capability_name, granted_by)
                        VALUES (?, ?, ?, ?)
                    """, (cap_id, agent_id, cap, approved_by))

            # Update approval record
            cursor.execute("""
                UPDATE agent_approvals
                SET status = 'approved', reviewed_by = ?, reviewed_at = ?, review_notes = ?
                WHERE agent_id = ? AND status = 'pending'
            """, (approved_by, datetime.utcnow().isoformat(), notes, agent_id))

            conn.commit()
            conn.close()

            # Update Firebase claims
            if self.firebase.is_available() and agent.firebase_uid:
                all_tags = list(set(agent.tags + (tags_granted or [])))
                all_caps = list(set(agent.capabilities + (capabilities_granted or [])))
                claims = AgentClaims(
                    agent_type=agent.metadata.get("agent_type", "general"),
                    machine_id=agent.machine_id,
                    tags=all_tags,
                    capabilities=all_caps,
                    approved_at=datetime.utcnow().isoformat()
                )
                self.firebase.set_agent_claims(agent_id, claims)

            logger.info(f"Approved agent {agent_id} by {approved_by}")
            return True

        except Exception as e:
            logger.error(f"Failed to approve agent {agent_id}: {e}")
            return False

    def reject_agent(self, agent_id: str, rejected_by: str, reason: str) -> bool:
        """Reject a pending agent"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE agent_identities
                SET status = ?
                WHERE agent_id = ? AND status = 'pending'
            """, (AgentStatus.REVOKED.value, agent_id))

            cursor.execute("""
                UPDATE agent_approvals
                SET status = 'rejected', reviewed_by = ?, reviewed_at = ?, review_notes = ?
                WHERE agent_id = ? AND status = 'pending'
            """, (rejected_by, datetime.utcnow().isoformat(), reason, agent_id))

            conn.commit()
            conn.close()

            # Disable Firebase user if exists
            agent = self.get_agent(agent_id)
            if agent and agent.firebase_uid and self.firebase.is_available():
                self.firebase.disable_agent(agent_id)

            logger.info(f"Rejected agent {agent_id} by {rejected_by}: {reason}")
            return True

        except Exception as e:
            logger.error(f"Failed to reject agent {agent_id}: {e}")
            return False

    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get all pending agent approvals"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT approval_id, agent_id, identity_id, requested_at, machine_id,
                       pre_auth_key_id, requested_tags, requested_capabilities
                FROM agent_approvals
                WHERE status = 'pending'
                ORDER BY requested_at ASC
            """)

            rows = cursor.fetchall()
            conn.close()

            return [{
                "approval_id": row[0],
                "agent_id": row[1],
                "identity_id": row[2],
                "requested_at": row[3],
                "machine_id": row[4],
                "pre_auth_key_id": row[5],
                "requested_tags": json.loads(row[6]) if row[6] else [],
                "requested_capabilities": json.loads(row[7]) if row[7] else []
            } for row in rows]

        except Exception as e:
            logger.error(f"Failed to get pending approvals: {e}")
            return []

    # ==================== Agent Revocation ====================

    def revoke_agent(self, agent_id: str, revoked_by: str, reason: str) -> bool:
        """Revoke an agent's access"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE agent_identities
                SET status = ?
                WHERE agent_id = ?
            """, (AgentStatus.REVOKED.value, agent_id))

            # Add to revocation list
            cursor.execute("""
                INSERT INTO token_revocations (revocation_id, agent_id, revoked_by, reason, expires_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                f"rev_{secrets.token_hex(8)}",
                agent_id,
                revoked_by,
                reason,
                (datetime.utcnow() + timedelta(days=30)).isoformat()
            ))

            conn.commit()
            conn.close()

            # Revoke Firebase tokens
            agent = self.get_agent(agent_id)
            if agent and agent.firebase_uid and self.firebase.is_available():
                self.firebase.revoke_agent_tokens(agent_id)
                self.firebase.disable_agent(agent_id)

            logger.info(f"Revoked agent {agent_id} by {revoked_by}: {reason}")
            return True

        except Exception as e:
            logger.error(f"Failed to revoke agent {agent_id}: {e}")
            return False

    # ==================== Audit Logging ====================

    def log_audit(
        self,
        action: str,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        permission_used: Optional[str] = None,
        grant_matched: Optional[str] = None,
        result: str = "success",
        denial_reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        machine_id: Optional[str] = None,
        request_metadata: Optional[Dict] = None,
        response_metadata: Optional[Dict] = None
    ):
        """Log an audit event"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO agent_audit_log (
                    agent_id, session_id, action, resource_type, resource_id,
                    permission_used, grant_matched, result, denial_reason,
                    ip_address, machine_id, request_metadata, response_metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                agent_id, session_id, action, resource_type, resource_id,
                permission_used, grant_matched, result, denial_reason,
                ip_address, machine_id,
                json.dumps(request_metadata or {}),
                json.dumps(response_metadata or {})
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")

    def get_audit_log(
        self,
        agent_id: Optional[str] = None,
        action_filter: Optional[str] = None,
        result_filter: Optional[str] = None,
        hours: int = 24,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get audit log entries"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

            query = "SELECT * FROM agent_audit_log WHERE timestamp >= ?"
            params = [since]

            if agent_id:
                query += " AND agent_id = ?"
                params.append(agent_id)
            if action_filter:
                query += " AND action = ?"
                params.append(action_filter)
            if result_filter:
                query += " AND result = ?"
                params.append(result_filter)

            query += f" ORDER BY timestamp DESC LIMIT {limit}"

            cursor.execute(query, params)
            rows = cursor.fetchall()
            columns = [d[0] for d in cursor.description]
            conn.close()

            return [dict(zip(columns, row)) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get audit log: {e}")
            return []


# Singleton instance
_agent_identity_system: Optional[AgentIdentitySystem] = None


def get_agent_identity_system() -> AgentIdentitySystem:
    """Get or create the agent identity system singleton"""
    global _agent_identity_system
    if _agent_identity_system is None:
        _agent_identity_system = AgentIdentitySystem()
    return _agent_identity_system
