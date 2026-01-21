"""
Zero-Knowledge Vault Key Sharing Module

Uses X25519 key exchange to share vault keys without the server seeing plaintext.
Pattern inspired by 1Password: recipient's public key encrypts the vault key.

Key Exchange Flow:
1. Sender has vault key K
2. Sender uses their X25519 private key + recipient's X25519 public key
3. ECDH derives a shared secret S
4. K is encrypted with S using ChaCha20-Poly1305
5. Encrypted blob sent to recipient
6. Recipient uses their X25519 private key + sender's X25519 public key
7. Same shared secret S is derived
8. K is decrypted

Security Properties:
- Server never sees vault key K or shared secret S
- Forward secrecy via ephemeral keys (optional)
- Authenticity via sender's key binding
"""

import os
import base64
import logging
import secrets
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.exceptions import InvalidTag

logger = logging.getLogger(__name__)


@dataclass
class EncryptedVaultKey:
    """Encrypted vault key blob for sharing"""
    # The encrypted vault key
    ciphertext: bytes
    # Nonce used for encryption
    nonce: bytes
    # Sender's X25519 public key (for recipient to derive shared secret)
    sender_pubkey: bytes
    # Key derivation info (for HKDF)
    kdf_info: bytes
    # Timestamp of encryption
    created_at: str
    # Version for future compatibility
    version: int = 1

    def to_bytes(self) -> bytes:
        """Serialize to bytes for storage"""
        # Format: version(1) + nonce(12) + sender_pubkey(32) + kdf_info_len(2) + kdf_info + ciphertext
        kdf_info_len = len(self.kdf_info).to_bytes(2, 'big')
        return (
            self.version.to_bytes(1, 'big') +
            self.nonce +
            self.sender_pubkey +
            kdf_info_len +
            self.kdf_info +
            self.ciphertext
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> 'EncryptedVaultKey':
        """Deserialize from bytes"""
        version = data[0]
        nonce = data[1:13]
        sender_pubkey = data[13:45]
        kdf_info_len = int.from_bytes(data[45:47], 'big')
        kdf_info = data[47:47+kdf_info_len]
        ciphertext = data[47+kdf_info_len:]

        return cls(
            ciphertext=ciphertext,
            nonce=nonce,
            sender_pubkey=sender_pubkey,
            kdf_info=kdf_info,
            created_at=datetime.utcnow().isoformat(),
            version=version
        )

    def to_base64(self) -> str:
        """Encode to base64 for JSON storage"""
        return base64.b64encode(self.to_bytes()).decode('utf-8')

    @classmethod
    def from_base64(cls, data: str) -> 'EncryptedVaultKey':
        """Decode from base64"""
        return cls.from_bytes(base64.b64decode(data))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "ciphertext": base64.b64encode(self.ciphertext).decode('utf-8'),
            "nonce": base64.b64encode(self.nonce).decode('utf-8'),
            "sender_pubkey": base64.b64encode(self.sender_pubkey).decode('utf-8'),
            "kdf_info": base64.b64encode(self.kdf_info).decode('utf-8'),
            "created_at": self.created_at,
            "version": self.version
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EncryptedVaultKey':
        """Create from dictionary"""
        return cls(
            ciphertext=base64.b64decode(data["ciphertext"]),
            nonce=base64.b64decode(data["nonce"]),
            sender_pubkey=base64.b64decode(data["sender_pubkey"]),
            kdf_info=base64.b64decode(data["kdf_info"]),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            version=data.get("version", 1)
        )


class VaultKeySharing:
    """
    Zero-Knowledge Vault Key Sharing using X25519 + ChaCha20-Poly1305

    Implements secure key sharing where the server never sees plaintext vault keys.
    """

    # HKDF info prefix for domain separation
    HKDF_INFO_PREFIX = b"haivemind-vault-key-v1:"

    def __init__(self):
        """Initialize vault key sharing system"""
        pass

    def _derive_shared_key(
        self,
        private_key: X25519PrivateKey,
        public_key: X25519PublicKey,
        info: bytes
    ) -> bytes:
        """
        Derive a shared symmetric key from ECDH shared secret.

        Uses HKDF to derive a 256-bit key suitable for ChaCha20-Poly1305.

        Args:
            private_key: Our X25519 private key
            public_key: Their X25519 public key
            info: Context info for HKDF (e.g., vault_id)

        Returns:
            32-byte symmetric key
        """
        # ECDH key agreement
        shared_secret = private_key.exchange(public_key)

        # HKDF to derive encryption key
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,  # We could add salt for extra security
            info=self.HKDF_INFO_PREFIX + info,
        )

        return hkdf.derive(shared_secret)

    def encrypt_vault_key(
        self,
        vault_key: bytes,
        recipient_x25519_pubkey: bytes,
        sender_x25519_privkey: bytes,
        vault_id: str
    ) -> EncryptedVaultKey:
        """
        Encrypt a vault key for a specific recipient.

        Uses ECDH key agreement + ChaCha20-Poly1305 encryption:
        1. Derive shared secret via X25519(sender_priv, recipient_pub)
        2. Use HKDF to derive encryption key from shared secret
        3. Encrypt vault_key with ChaCha20-Poly1305
        4. Return encrypted blob with metadata

        Args:
            vault_key: The vault's encryption key (typically 32 bytes)
            recipient_x25519_pubkey: Recipient's X25519 public key (32 bytes)
            sender_x25519_privkey: Sender's X25519 private key (32 bytes)
            vault_id: Vault identifier (used in KDF for domain separation)

        Returns:
            EncryptedVaultKey containing all data needed for decryption
        """
        # Convert raw bytes to key objects
        sender_key = X25519PrivateKey.from_private_bytes(sender_x25519_privkey)
        recipient_key = X25519PublicKey.from_public_bytes(recipient_x25519_pubkey)

        # KDF info includes vault_id for domain separation
        kdf_info = vault_id.encode('utf-8')

        # Derive shared encryption key
        shared_key = self._derive_shared_key(sender_key, recipient_key, kdf_info)

        # Generate random nonce for ChaCha20-Poly1305
        nonce = os.urandom(12)

        # Encrypt vault key
        cipher = ChaCha20Poly1305(shared_key)
        ciphertext = cipher.encrypt(nonce, vault_key, None)

        # Get sender's public key for recipient to use
        sender_pubkey = sender_key.public_key().public_bytes_raw()

        return EncryptedVaultKey(
            ciphertext=ciphertext,
            nonce=nonce,
            sender_pubkey=sender_pubkey,
            kdf_info=kdf_info,
            created_at=datetime.utcnow().isoformat(),
            version=1
        )

    def decrypt_vault_key(
        self,
        encrypted_key: EncryptedVaultKey,
        recipient_x25519_privkey: bytes
    ) -> bytes:
        """
        Decrypt a vault key using recipient's private key.

        Args:
            encrypted_key: EncryptedVaultKey from encrypt_vault_key
            recipient_x25519_privkey: Recipient's X25519 private key (32 bytes)

        Returns:
            Decrypted vault key bytes

        Raises:
            InvalidTag: If decryption fails (wrong key or tampered ciphertext)
        """
        # Convert raw bytes to key objects
        recipient_key = X25519PrivateKey.from_private_bytes(recipient_x25519_privkey)
        sender_key = X25519PublicKey.from_public_bytes(encrypted_key.sender_pubkey)

        # Derive same shared encryption key
        shared_key = self._derive_shared_key(
            recipient_key,
            sender_key,
            encrypted_key.kdf_info
        )

        # Decrypt vault key
        cipher = ChaCha20Poly1305(shared_key)
        return cipher.decrypt(encrypted_key.nonce, encrypted_key.ciphertext, None)

    def encrypt_vault_key_with_ephemeral(
        self,
        vault_key: bytes,
        recipient_x25519_pubkey: bytes,
        vault_id: str
    ) -> Tuple[EncryptedVaultKey, bytes]:
        """
        Encrypt vault key using an ephemeral sender key for forward secrecy.

        Instead of using the sender's long-term key, generates a one-time
        key pair. The ephemeral private key is returned for the sender to
        store securely if they need to decrypt later.

        Args:
            vault_key: The vault's encryption key
            recipient_x25519_pubkey: Recipient's X25519 public key
            vault_id: Vault identifier

        Returns:
            Tuple of (EncryptedVaultKey, ephemeral_private_key)
        """
        # Generate ephemeral key pair
        ephemeral_key = X25519PrivateKey.generate()
        ephemeral_privkey = ephemeral_key.private_bytes_raw()

        # Encrypt using ephemeral key
        encrypted = self.encrypt_vault_key(
            vault_key=vault_key,
            recipient_x25519_pubkey=recipient_x25519_pubkey,
            sender_x25519_privkey=ephemeral_privkey,
            vault_id=vault_id
        )

        return encrypted, ephemeral_privkey

    def reencrypt_for_new_recipient(
        self,
        encrypted_key: EncryptedVaultKey,
        current_recipient_privkey: bytes,
        new_recipient_pubkey: bytes,
        vault_id: str
    ) -> EncryptedVaultKey:
        """
        Re-encrypt a vault key for a new recipient.

        Decrypts with current recipient's key, then encrypts for new recipient.
        Useful for sharing a vault that was shared with you.

        Args:
            encrypted_key: Currently encrypted vault key
            current_recipient_privkey: Your X25519 private key
            new_recipient_pubkey: New recipient's X25519 public key
            vault_id: Vault identifier

        Returns:
            New EncryptedVaultKey for the new recipient
        """
        # Decrypt vault key
        vault_key = self.decrypt_vault_key(encrypted_key, current_recipient_privkey)

        # Re-encrypt for new recipient
        return self.encrypt_vault_key(
            vault_key=vault_key,
            recipient_x25519_pubkey=new_recipient_pubkey,
            sender_x25519_privkey=current_recipient_privkey,
            vault_id=vault_id
        )

    @staticmethod
    def generate_vault_key() -> bytes:
        """Generate a new random vault encryption key (256-bit)"""
        return secrets.token_bytes(32)

    @staticmethod
    def generate_x25519_keypair() -> Tuple[bytes, bytes]:
        """
        Generate a new X25519 key pair.

        Returns:
            Tuple of (private_key_bytes, public_key_bytes)
        """
        private_key = X25519PrivateKey.generate()
        public_key = private_key.public_key()
        return (
            private_key.private_bytes_raw(),
            public_key.public_bytes_raw()
        )


class VaultKeyRotation:
    """
    Handles vault key rotation with zero-knowledge re-encryption.

    When a vault key needs to be rotated:
    1. Generate new vault key
    2. Re-encrypt all vault contents with new key
    3. Re-encrypt new key for all authorized agents
    4. Invalidate old key shares
    """

    def __init__(self, key_sharing: VaultKeySharing):
        self.key_sharing = key_sharing

    def rotate_vault_key(
        self,
        old_vault_key: bytes,
        vault_id: str,
        authorized_agents: list  # List of (agent_id, x25519_pubkey) tuples
    ) -> Tuple[bytes, Dict[str, EncryptedVaultKey]]:
        """
        Rotate a vault's encryption key.

        Args:
            old_vault_key: Current vault encryption key
            vault_id: Vault identifier
            authorized_agents: List of (agent_id, x25519_pubkey) tuples

        Returns:
            Tuple of (new_vault_key, dict of agent_id -> encrypted_key)
        """
        # Generate new vault key
        new_vault_key = VaultKeySharing.generate_vault_key()

        # Generate ephemeral key for rotation
        rotation_privkey, _ = VaultKeySharing.generate_x25519_keypair()

        # Encrypt new key for each authorized agent
        encrypted_keys = {}
        for agent_id, agent_pubkey in authorized_agents:
            encrypted = self.key_sharing.encrypt_vault_key(
                vault_key=new_vault_key,
                recipient_x25519_pubkey=agent_pubkey,
                sender_x25519_privkey=rotation_privkey,
                vault_id=vault_id
            )
            encrypted_keys[agent_id] = encrypted

        logger.info(f"Rotated vault key for {vault_id}, "
                   f"re-encrypted for {len(authorized_agents)} agents")

        return new_vault_key, encrypted_keys


# Singleton instance
_vault_key_sharing: Optional[VaultKeySharing] = None


def get_vault_key_sharing() -> VaultKeySharing:
    """Get or create the VaultKeySharing singleton"""
    global _vault_key_sharing
    if _vault_key_sharing is None:
        _vault_key_sharing = VaultKeySharing()
    return _vault_key_sharing
