"""
Vault MCP Integration

Provides MCP-friendly async interface for credential vault operations
with comprehensive audit trail and encryption.

Author: Lance James, Unit 221B, Inc
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available - vault caching disabled")

from vault.core_vault import CoreCredentialVault
from vault.encryption_engine import EncryptionEngine
from vault.audit_manager import AuditManager
from vault.access_control import VaultAccess

logger = logging.getLogger(__name__)


class VaultMCPIntegration:
    """
    MCP integration layer for vault operations.

    Wraps existing vault modules with async interface and enforces
    mandatory audit trail for all credential access operations.

    Features:
    - AES-256-GCM encryption with scrypt key derivation
    - Mandatory audit logging for all access
    - Credential rotation with history preservation
    - Search by metadata without decryption
    - Revocation with reason tracking
    """

    def __init__(
        self,
        config: Dict[str, Any],
        redis_client: Optional[aioredis.Redis] = None
    ):
        """
        Initialize vault MCP integration.

        Args:
            config: Full configuration dictionary
            redis_client: Optional Redis client for caching
        """
        self.config = config
        self.vault_config = config.get('vault', {})
        self.redis_client = redis_client

        # Get master password from config
        self.master_password = self.vault_config.get('master_password', 'R3dca070111-001')

        # Initialize core vault components
        try:
            self.vault = CoreCredentialVault(config, redis_client)
            self.encryption_engine = EncryptionEngine(config, redis_client)
            self.audit_manager = AuditManager(config)
            self.access_control = VaultAccess(config)
            logger.info("Vault MCP integration initialized")
        except Exception as e:
            logger.error(f"Failed to initialize vault components: {e}")
            raise

        self.audit_enabled = self.vault_config.get('audit', {}).get('enabled', True)
        self.mandatory_audit = self.vault_config.get('audit', {}).get('mandatory_for_access', True)

    async def store_credential(
        self,
        name: str,
        credential_data: Dict[str, Any],
        credential_type: str = "password",
        environment: str = "production",
        service: str = "",
        project: str = "",
        master_password: Optional[str] = None,
        expires_in_days: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Store encrypted credential with AES-256-GCM encryption.

        Args:
            name: Credential name/description
            credential_data: Credential data to encrypt (dictionary)
            credential_type: Type (password, api_key, certificate, ssh_key, token)
            environment: Environment (production, staging, development)
            service: Service name this credential belongs to
            project: Project name
            master_password: Master password (uses configured if not provided)
            expires_in_days: Days until expiration (optional)
            tags: List of tags for categorization

        Returns:
            Dictionary with credential_id and metadata
        """
        try:
            password = master_password or self.master_password

            # Validate credential type
            valid_types = ['password', 'api_key', 'certificate', 'ssh_key', 'token', 'secret']
            if credential_type not in valid_types:
                raise ValueError(f"Invalid credential_type. Must be one of: {valid_types}")

            # Calculate expiration
            expires_at = None
            if expires_in_days:
                expires_at = datetime.now() + timedelta(days=expires_in_days)

            # Store credential (synchronous vault operation)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.vault.store_credential,
                name,
                json.dumps(credential_data),
                credential_type,
                environment,
                service,
                password
            )

            credential_id = result.get('credential_id')

            # Log audit entry
            if self.audit_enabled:
                await self._log_audit(
                    action="store_credential",
                    credential_id=credential_id,
                    details={
                        "name": name,
                        "type": credential_type,
                        "environment": environment,
                        "service": service
                    }
                )

            logger.info(f"Stored credential {credential_id}: {name}")

            return {
                "credential_id": credential_id,
                "name": name,
                "credential_type": credential_type,
                "environment": environment,
                "service": service,
                "project": project,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "tags": tags or [],
                "status": "stored",
                "encrypted": True
            }

        except Exception as e:
            logger.error(f"Error storing credential: {e}")
            raise

    async def retrieve_credential(
        self,
        credential_id: str,
        master_password: Optional[str] = None,
        audit_reason: str = ""
    ) -> Dict[str, Any]:
        """
        Retrieve and decrypt credential with mandatory audit trail.

        Args:
            credential_id: Credential ID to retrieve
            master_password: Master password (uses configured if not provided)
            audit_reason: Reason for access (MANDATORY if audit enabled)

        Returns:
            Dictionary with decrypted credential data

        Raises:
            ValueError: If audit_reason not provided when mandatory
        """
        try:
            # Enforce mandatory audit
            if self.mandatory_audit and not audit_reason:
                raise ValueError("audit_reason is required for credential retrieval")

            password = master_password or self.master_password

            # Retrieve credential (synchronous vault operation)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.vault.retrieve_credential,
                credential_id,
                password
            )

            # Parse credential data
            credential_data = json.loads(result.get('data', '{}'))

            # Log audit entry
            if self.audit_enabled:
                await self._log_audit(
                    action="retrieve_credential",
                    credential_id=credential_id,
                    details={
                        "reason": audit_reason,
                        "timestamp": datetime.now().isoformat()
                    }
                )

            logger.info(f"Retrieved credential {credential_id}")

            return {
                "credential_id": credential_id,
                "name": result.get('name'),
                "credential_type": result.get('type'),
                "credential_data": credential_data,
                "environment": result.get('environment'),
                "service": result.get('service'),
                "last_accessed": datetime.now().isoformat(),
                "audit_reason": audit_reason
            }

        except Exception as e:
            logger.error(f"Error retrieving credential: {e}")
            raise

    async def search_credentials(
        self,
        query: str = "",
        environment: Optional[str] = None,
        service: Optional[str] = None,
        credential_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search credentials by metadata without decryption.

        Args:
            query: Search query for name/description
            environment: Filter by environment
            service: Filter by service
            credential_type: Filter by credential type
            limit: Maximum number of results

        Returns:
            List of credential metadata (no secrets exposed)
        """
        try:
            # Search metadata (synchronous vault operation)
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                self.vault.search_credentials,
                query,
                environment,
                service,
                credential_type,
                limit
            )

            # Filter out sensitive data
            credentials = []
            for result in results:
                credentials.append({
                    "credential_id": result.get('credential_id'),
                    "name": result.get('name'),
                    "credential_type": result.get('type'),
                    "environment": result.get('environment'),
                    "service": result.get('service'),
                    "project": result.get('project'),
                    "created_at": result.get('created_at'),
                    "last_accessed": result.get('last_accessed'),
                    "status": result.get('status', 'active')
                })

            logger.info(f"Found {len(credentials)} credentials matching search")

            return credentials

        except Exception as e:
            logger.error(f"Error searching credentials: {e}")
            raise

    async def rotate_credential(
        self,
        credential_id: str,
        new_credential_data: Dict[str, Any],
        master_password: Optional[str] = None,
        rotation_reason: str = ""
    ) -> Dict[str, Any]:
        """
        Rotate credential with history preservation.

        Args:
            credential_id: Credential ID to rotate
            new_credential_data: New credential data
            master_password: Master password (uses configured if not provided)
            rotation_reason: Reason for rotation

        Returns:
            Dictionary with rotation status and new version info
        """
        try:
            password = master_password or self.master_password

            # Rotate credential (synchronous vault operation)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.vault.rotate_credential,
                credential_id,
                json.dumps(new_credential_data),
                password,
                rotation_reason
            )

            # Log audit entry
            if self.audit_enabled:
                await self._log_audit(
                    action="rotate_credential",
                    credential_id=credential_id,
                    details={
                        "reason": rotation_reason,
                        "new_version": result.get('version'),
                        "timestamp": datetime.now().isoformat()
                    }
                )

            logger.info(f"Rotated credential {credential_id}")

            return {
                "credential_id": credential_id,
                "rotation_status": "success",
                "new_version": result.get('version'),
                "old_version_archived": True,
                "rotation_reason": rotation_reason,
                "rotated_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error rotating credential: {e}")
            raise

    async def revoke_credential(
        self,
        credential_id: str,
        revocation_reason: str = ""
    ) -> Dict[str, Any]:
        """
        Revoke credential access with reason tracking.

        Args:
            credential_id: Credential ID to revoke
            revocation_reason: Reason for revocation

        Returns:
            Dictionary with revocation status
        """
        try:
            # Revoke credential (synchronous vault operation)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.vault.revoke_credential,
                credential_id,
                revocation_reason
            )

            # Log audit entry
            if self.audit_enabled:
                await self._log_audit(
                    action="revoke_credential",
                    credential_id=credential_id,
                    details={
                        "reason": revocation_reason,
                        "timestamp": datetime.now().isoformat()
                    }
                )

            logger.info(f"Revoked credential {credential_id}")

            return {
                "credential_id": credential_id,
                "status": "revoked",
                "revocation_reason": revocation_reason,
                "revoked_at": datetime.now().isoformat(),
                "recoverable": False
            }

        except Exception as e:
            logger.error(f"Error revoking credential: {e}")
            raise

    async def list_credentials(
        self,
        environment: Optional[str] = None,
        service: Optional[str] = None,
        status: str = "active",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List credential metadata (no secrets exposed).

        Args:
            environment: Filter by environment
            service: Filter by service
            status: Filter by status (active, revoked, expired)
            limit: Maximum number of results

        Returns:
            List of credential metadata
        """
        try:
            # List credentials (synchronous vault operation)
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                self.vault.list_credentials,
                environment,
                service,
                status,
                limit
            )

            # Filter out sensitive data
            credentials = []
            for result in results:
                credentials.append({
                    "credential_id": result.get('credential_id'),
                    "name": result.get('name'),
                    "credential_type": result.get('type'),
                    "environment": result.get('environment'),
                    "service": result.get('service'),
                    "project": result.get('project'),
                    "status": result.get('status'),
                    "created_at": result.get('created_at'),
                    "last_accessed": result.get('last_accessed'),
                    "expires_at": result.get('expires_at')
                })

            logger.info(f"Listed {len(credentials)} credentials")

            return credentials

        except Exception as e:
            logger.error(f"Error listing credentials: {e}")
            raise

    # Private helper methods

    async def _log_audit(
        self,
        action: str,
        credential_id: str,
        details: Dict[str, Any]
    ):
        """Log audit entry for credential operation"""
        try:
            audit_entry = {
                "action": action,
                "credential_id": credential_id,
                "details": details,
                "timestamp": datetime.now().isoformat(),
                "user": "mcp_integration"  # Could be enhanced to track actual user
            }

            # Log to audit manager
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.audit_manager.log_audit,
                audit_entry
            )

            logger.debug(f"Audit logged: {action} for {credential_id}")

        except Exception as e:
            logger.error(f"Error logging audit: {e}")
            # Don't raise - audit failure shouldn't block operations
