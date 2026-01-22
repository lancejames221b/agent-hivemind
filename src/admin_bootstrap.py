#!/usr/bin/env python3
"""
hAIveMind Admin Bootstrap System

Handles the chicken-egg problem of needing credentials to access
the vault that stores credentials.

Security Model:
1. First run generates master credentials and stores them in vault
2. Bootstrap key (stored securely on disk) unlocks the system vault
3. All admin credentials (password hash, JWT secret, API tokens) in vault
4. Config.json contains NO sensitive values - only references

Bootstrap Flow:
1. Check for existing bootstrap key at data/.bootstrap_key
2. If first run: Generate all credentials, store in vault, return one-time credentials
3. If subsequent: Load credentials from vault using bootstrap key

Author: Lance James, Unit 221B Inc
"""

import os
import json
import secrets
import sqlite3
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False

try:
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class SystemCredentials:
    """Container for system credentials loaded from vault"""
    admin_password_hash: bytes
    jwt_secret: str
    admin_token: str
    readonly_token: str
    agent_token: str
    vault_master_key: bytes
    initialized_at: str
    last_rotation: Optional[str] = None


class AdminBootstrap:
    """
    Secure Admin System Bootstrap

    Manages the initialization and loading of system credentials
    from the hAIveMind vault system.
    """

    BOOTSTRAP_KEY_PATH = "data/.bootstrap_key"
    SYSTEM_VAULT_ID = "system-credentials"
    CREDENTIALS_DB_PATH = "data/admin_credentials.db"

    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path) if base_path else Path(__file__).parent.parent
        self.bootstrap_key_path = self.base_path / self.BOOTSTRAP_KEY_PATH
        self.credentials_db_path = self.base_path / self.CREDENTIALS_DB_PATH
        self._credentials: Optional[SystemCredentials] = None
        self._initialized = False

        # Ensure data directory exists
        self.bootstrap_key_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize credentials database
        self._init_credentials_db()

    def _init_credentials_db(self):
        """Initialize the encrypted credentials database"""
        with sqlite3.connect(self.credentials_db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_credentials (
                    key TEXT PRIMARY KEY,
                    encrypted_value BLOB NOT NULL,
                    nonce BLOB NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bootstrap_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    actor TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    details TEXT DEFAULT '{}'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS credential_rotations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    credential_key TEXT NOT NULL,
                    rotated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    rotated_by TEXT,
                    reason TEXT
                )
            """)
            conn.commit()

    def is_initialized(self) -> bool:
        """Check if the system has been initialized with credentials"""
        return self.bootstrap_key_path.exists() and self._has_credentials()

    def _has_credentials(self) -> bool:
        """Check if credentials exist in the database"""
        try:
            with sqlite3.connect(self.credentials_db_path) as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM system_credentials WHERE key = ?",
                    ("admin/password_hash",)
                )
                return cursor.fetchone()[0] > 0
        except:
            return False

    def initialize_system(self, admin_username: str = "admin") -> Dict[str, Any]:
        """
        Initialize the admin system with secure credentials.

        This should only be called once during first-run setup.
        Returns credentials that should be saved securely - shown only once!

        Args:
            admin_username: Username for admin account (default: admin)

        Returns:
            Dictionary with one-time credentials display
        """
        if self.is_initialized():
            raise RuntimeError("System already initialized. Use reset_system() to reinitialize.")

        logger.info("Initializing hAIveMind admin system (first run)...")

        # Generate bootstrap key (used to decrypt credentials)
        bootstrap_key = secrets.token_bytes(32)

        # Generate all credentials
        admin_password = secrets.token_urlsafe(16)
        jwt_secret = secrets.token_urlsafe(64)
        admin_token = f"haiv_admin_{secrets.token_urlsafe(32)}"
        readonly_token = f"haiv_readonly_{secrets.token_urlsafe(32)}"
        agent_token = f"haiv_agent_{secrets.token_urlsafe(32)}"
        vault_master_key = secrets.token_bytes(32)

        # Hash the admin password
        if BCRYPT_AVAILABLE:
            admin_password_hash = bcrypt.hashpw(admin_password.encode(), bcrypt.gensalt(12))
        else:
            # Fallback to SHA256 (less secure but functional)
            admin_password_hash = hashlib.sha256(admin_password.encode()).digest()
            logger.warning("bcrypt not available, using SHA256 for password hashing")

        # Store credentials encrypted with bootstrap key
        credentials = {
            "admin/username": admin_username,
            "admin/password_hash": admin_password_hash,
            "admin/jwt_secret": jwt_secret,
            "api/admin_token": admin_token,
            "api/readonly_token": readonly_token,
            "api/agent_token": agent_token,
            "vault/master_key": vault_master_key,
            "system/initialized_at": datetime.utcnow().isoformat(),
        }

        # Encrypt and store each credential
        for key, value in credentials.items():
            self._store_encrypted_credential(key, value, bootstrap_key)

        # Store bootstrap key with restricted permissions
        self._store_bootstrap_key(bootstrap_key)

        # Log the initialization
        self._audit_log("system_initialized", "bootstrap", {
            "admin_username": admin_username,
            "credentials_count": len(credentials)
        })

        self._initialized = True

        return {
            "status": "initialized",
            "message": "System initialized successfully. SAVE THESE CREDENTIALS - SHOWN ONLY ONCE!",
            "credentials": {
                "admin_username": admin_username,
                "admin_password": admin_password,
                "admin_token": admin_token,
                "readonly_token": readonly_token,
                "agent_token": agent_token,
            },
            "bootstrap_key": bootstrap_key.hex(),
            "instructions": [
                "1. Save the admin password securely - it cannot be recovered",
                "2. Store the bootstrap_key in a secure location for disaster recovery",
                "3. API tokens can be rotated later via the admin panel",
                "4. Set HAIVEMIND_BOOTSTRAP_KEY environment variable for automated deployments"
            ]
        }

    def _store_encrypted_credential(self, key: str, value: Any, bootstrap_key: bytes):
        """Store a credential encrypted with the bootstrap key"""
        # Convert value to bytes
        if isinstance(value, str):
            value_bytes = value.encode('utf-8')
        elif isinstance(value, bytes):
            value_bytes = value
        else:
            value_bytes = json.dumps(value).encode('utf-8')

        # Encrypt with ChaCha20-Poly1305 if available, otherwise XOR
        if CRYPTO_AVAILABLE:
            nonce = secrets.token_bytes(12)
            cipher = ChaCha20Poly1305(bootstrap_key)
            encrypted = cipher.encrypt(nonce, value_bytes, None)
        else:
            # Simple XOR encryption (less secure fallback)
            nonce = secrets.token_bytes(12)
            encrypted = bytes(a ^ b for a, b in zip(value_bytes, (bootstrap_key * (len(value_bytes) // 32 + 1))[:len(value_bytes)]))
            logger.warning("cryptography not available, using XOR encryption")

        # Store in database
        with sqlite3.connect(self.credentials_db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO system_credentials (key, encrypted_value, nonce, updated_at)
                VALUES (?, ?, ?, ?)
            """, (key, encrypted, nonce, datetime.utcnow().isoformat()))
            conn.commit()

    def _load_encrypted_credential(self, key: str, bootstrap_key: bytes) -> Optional[bytes]:
        """Load and decrypt a credential"""
        try:
            with sqlite3.connect(self.credentials_db_path) as conn:
                cursor = conn.execute(
                    "SELECT encrypted_value, nonce FROM system_credentials WHERE key = ?",
                    (key,)
                )
                row = cursor.fetchone()
                if not row:
                    return None

                encrypted, nonce = row

                # Decrypt
                if CRYPTO_AVAILABLE:
                    cipher = ChaCha20Poly1305(bootstrap_key)
                    return cipher.decrypt(nonce, encrypted, None)
                else:
                    # XOR decryption
                    return bytes(a ^ b for a, b in zip(encrypted, (bootstrap_key * (len(encrypted) // 32 + 1))[:len(encrypted)]))
        except Exception as e:
            logger.error(f"Failed to load credential {key}: {e}")
            return None

    def _store_bootstrap_key(self, bootstrap_key: bytes):
        """Store bootstrap key with restricted file permissions"""
        # Write key
        with open(self.bootstrap_key_path, 'wb') as f:
            f.write(bootstrap_key)

        # Set restrictive permissions (owner read/write only)
        os.chmod(self.bootstrap_key_path, 0o600)

        logger.info(f"Bootstrap key stored at {self.bootstrap_key_path} (permissions: 0600)")

    def _load_bootstrap_key(self) -> Optional[bytes]:
        """Load bootstrap key from file or environment"""
        # First check environment variable
        env_key = os.environ.get('HAIVEMIND_BOOTSTRAP_KEY')
        if env_key:
            try:
                return bytes.fromhex(env_key)
            except ValueError:
                logger.warning("Invalid HAIVEMIND_BOOTSTRAP_KEY format (expected hex)")

        # Load from file
        if self.bootstrap_key_path.exists():
            with open(self.bootstrap_key_path, 'rb') as f:
                return f.read()

        return None

    def load_credentials(self) -> SystemCredentials:
        """
        Load system credentials from vault.

        Returns:
            SystemCredentials object with all system credentials

        Raises:
            RuntimeError: If system not initialized or bootstrap key missing
        """
        if not self.is_initialized():
            raise RuntimeError("System not initialized. Call initialize_system() first.")

        bootstrap_key = self._load_bootstrap_key()
        if not bootstrap_key:
            raise RuntimeError("Bootstrap key not found. Set HAIVEMIND_BOOTSTRAP_KEY or check data/.bootstrap_key")

        # Load all credentials
        admin_password_hash = self._load_encrypted_credential("admin/password_hash", bootstrap_key)
        jwt_secret = self._load_encrypted_credential("admin/jwt_secret", bootstrap_key)
        admin_token = self._load_encrypted_credential("api/admin_token", bootstrap_key)
        readonly_token = self._load_encrypted_credential("api/readonly_token", bootstrap_key)
        agent_token = self._load_encrypted_credential("api/agent_token", bootstrap_key)
        vault_master_key = self._load_encrypted_credential("vault/master_key", bootstrap_key)
        initialized_at = self._load_encrypted_credential("system/initialized_at", bootstrap_key)

        self._credentials = SystemCredentials(
            admin_password_hash=admin_password_hash,
            jwt_secret=jwt_secret.decode() if jwt_secret else None,
            admin_token=admin_token.decode() if admin_token else None,
            readonly_token=readonly_token.decode() if readonly_token else None,
            agent_token=agent_token.decode() if agent_token else None,
            vault_master_key=vault_master_key,
            initialized_at=initialized_at.decode() if initialized_at else None
        )

        self._audit_log("credentials_loaded", "system", {})

        return self._credentials

    def verify_admin_password(self, password: str) -> bool:
        """
        Verify an admin password against the stored hash.

        Args:
            password: Password to verify

        Returns:
            True if password matches, False otherwise
        """
        if not self._credentials:
            self.load_credentials()

        if not self._credentials or not self._credentials.admin_password_hash:
            return False

        if BCRYPT_AVAILABLE:
            try:
                return bcrypt.checkpw(password.encode(), self._credentials.admin_password_hash)
            except Exception:
                return False
        else:
            # SHA256 fallback
            return hashlib.sha256(password.encode()).digest() == self._credentials.admin_password_hash

    def get_jwt_secret(self) -> str:
        """Get the JWT signing secret"""
        if not self._credentials:
            self.load_credentials()
        return self._credentials.jwt_secret

    def get_admin_token(self) -> str:
        """Get the admin API token"""
        if not self._credentials:
            self.load_credentials()
        return self._credentials.admin_token

    def get_vault_master_key(self) -> bytes:
        """Get the vault master encryption key"""
        if not self._credentials:
            self.load_credentials()
        return self._credentials.vault_master_key

    def rotate_credential(self, credential_type: str, rotated_by: str = "admin", reason: str = None) -> Dict[str, Any]:
        """
        Rotate a specific credential.

        Args:
            credential_type: Type of credential to rotate (jwt_secret, admin_token, etc.)
            rotated_by: Who is performing the rotation
            reason: Reason for rotation

        Returns:
            Dictionary with new credential value (shown once)
        """
        bootstrap_key = self._load_bootstrap_key()
        if not bootstrap_key:
            raise RuntimeError("Bootstrap key not found")

        credential_map = {
            "jwt_secret": ("admin/jwt_secret", lambda: secrets.token_urlsafe(64)),
            "admin_token": ("api/admin_token", lambda: f"haiv_admin_{secrets.token_urlsafe(32)}"),
            "readonly_token": ("api/readonly_token", lambda: f"haiv_readonly_{secrets.token_urlsafe(32)}"),
            "agent_token": ("api/agent_token", lambda: f"haiv_agent_{secrets.token_urlsafe(32)}"),
        }

        if credential_type not in credential_map:
            raise ValueError(f"Unknown credential type: {credential_type}")

        key, generator = credential_map[credential_type]
        new_value = generator()

        # Store new value
        self._store_encrypted_credential(key, new_value, bootstrap_key)

        # Log rotation
        with sqlite3.connect(self.credentials_db_path) as conn:
            conn.execute("""
                INSERT INTO credential_rotations (credential_key, rotated_by, reason)
                VALUES (?, ?, ?)
            """, (key, rotated_by, reason))
            conn.commit()

        self._audit_log("credential_rotated", rotated_by, {
            "credential_type": credential_type,
            "reason": reason
        })

        # Clear cached credentials to force reload
        self._credentials = None

        return {
            "status": "rotated",
            "credential_type": credential_type,
            "new_value": new_value,
            "message": "Credential rotated successfully. Save the new value!"
        }

    def reset_admin_password(self, new_password: str = None, reset_by: str = "admin") -> Dict[str, Any]:
        """
        Reset the admin password.

        Args:
            new_password: New password (generated if not provided)
            reset_by: Who is performing the reset

        Returns:
            Dictionary with new password (shown once)
        """
        bootstrap_key = self._load_bootstrap_key()
        if not bootstrap_key:
            raise RuntimeError("Bootstrap key not found")

        if not new_password:
            new_password = secrets.token_urlsafe(16)

        # Hash new password
        if BCRYPT_AVAILABLE:
            new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt(12))
        else:
            new_hash = hashlib.sha256(new_password.encode()).digest()

        # Store new hash
        self._store_encrypted_credential("admin/password_hash", new_hash, bootstrap_key)

        self._audit_log("admin_password_reset", reset_by, {})

        # Clear cached credentials
        self._credentials = None

        return {
            "status": "reset",
            "new_password": new_password,
            "message": "Admin password reset successfully. Save the new password!"
        }

    def _audit_log(self, action: str, actor: str, details: Dict):
        """Log an audit event"""
        try:
            with sqlite3.connect(self.credentials_db_path) as conn:
                conn.execute("""
                    INSERT INTO bootstrap_audit (action, actor, details)
                    VALUES (?, ?, ?)
                """, (action, actor, json.dumps(details)))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")

    def get_audit_log(self, limit: int = 100) -> list:
        """Get recent audit log entries"""
        with sqlite3.connect(self.credentials_db_path) as conn:
            cursor = conn.execute("""
                SELECT action, actor, timestamp, details
                FROM bootstrap_audit
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            return [
                {
                    "action": row[0],
                    "actor": row[1],
                    "timestamp": row[2],
                    "details": json.loads(row[3]) if row[3] else {}
                }
                for row in cursor.fetchall()
            ]


# Global bootstrap instance
_bootstrap_instance: Optional[AdminBootstrap] = None


def get_admin_bootstrap(base_path: str = None) -> AdminBootstrap:
    """Get the global AdminBootstrap instance"""
    global _bootstrap_instance
    if _bootstrap_instance is None:
        _bootstrap_instance = AdminBootstrap(base_path)
    return _bootstrap_instance


def initialize_admin_system(admin_username: str = "admin") -> Dict[str, Any]:
    """Convenience function to initialize the admin system"""
    bootstrap = get_admin_bootstrap()
    return bootstrap.initialize_system(admin_username)


def verify_admin_credentials(password: str) -> bool:
    """Convenience function to verify admin credentials"""
    bootstrap = get_admin_bootstrap()
    return bootstrap.verify_admin_password(password)


if __name__ == "__main__":
    # CLI for initialization
    import sys

    bootstrap = AdminBootstrap()

    if len(sys.argv) > 1 and sys.argv[1] == "init":
        if bootstrap.is_initialized():
            print("System already initialized!")
            sys.exit(1)

        result = bootstrap.initialize_system()
        print("\n" + "="*60)
        print("HAIVEMIND ADMIN SYSTEM INITIALIZED")
        print("="*60)
        print(f"\nAdmin Username: {result['credentials']['admin_username']}")
        print(f"Admin Password: {result['credentials']['admin_password']}")
        print(f"\nAdmin Token: {result['credentials']['admin_token']}")
        print(f"Readonly Token: {result['credentials']['readonly_token']}")
        print(f"Agent Token: {result['credentials']['agent_token']}")
        print(f"\nBootstrap Key: {result['bootstrap_key']}")
        print("\n" + "="*60)
        print("SAVE THESE CREDENTIALS - SHOWN ONLY ONCE!")
        print("="*60 + "\n")

    elif len(sys.argv) > 1 and sys.argv[1] == "status":
        if bootstrap.is_initialized():
            print("System Status: INITIALIZED")
            try:
                creds = bootstrap.load_credentials()
                print(f"Initialized At: {creds.initialized_at}")
            except Exception as e:
                print(f"Warning: Could not load credentials: {e}")
        else:
            print("System Status: NOT INITIALIZED")
            print("Run: python admin_bootstrap.py init")

    else:
        print("Usage:")
        print("  python admin_bootstrap.py init    - Initialize the admin system")
        print("  python admin_bootstrap.py status  - Check initialization status")
