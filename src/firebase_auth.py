"""
Firebase Authentication Module for hAIveMind Agent Auth System

Provides Firebase Admin SDK integration for:
- Custom token minting for agents
- Token verification with custom claims
- Token revocation
- Agent user management
"""

import os
import logging
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Try to import Firebase Admin SDK
try:
    import firebase_admin
    from firebase_admin import credentials, auth
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    logger.warning("Firebase Admin SDK not installed. Install with: pip install firebase-admin")


@dataclass
class AgentClaims:
    """Custom claims structure for agent tokens"""
    agent_type: str
    machine_id: str
    tags: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    confidentiality_max: str = "normal"
    approved_at: Optional[str] = None
    expires_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firebase custom claims"""
        return {
            "agent_type": self.agent_type,
            "machine_id": self.machine_id,
            "tags": self.tags,
            "capabilities": self.capabilities,
            "confidentiality_max": self.confidentiality_max,
            "approved_at": self.approved_at,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentClaims":
        """Create from dictionary"""
        return cls(
            agent_type=data.get("agent_type", "unknown"),
            machine_id=data.get("machine_id", "unknown"),
            tags=data.get("tags", []),
            capabilities=data.get("capabilities", []),
            confidentiality_max=data.get("confidentiality_max", "normal"),
            approved_at=data.get("approved_at"),
            expires_at=data.get("expires_at"),
        )


@dataclass
class TokenVerificationResult:
    """Result of token verification"""
    valid: bool
    uid: Optional[str] = None
    claims: Optional[AgentClaims] = None
    error: Optional[str] = None
    revoked: bool = False


class FirebaseAgentAuth:
    """
    Firebase Authentication for hAIveMind Agents

    Implements Tailscale-style auth with Firebase as the identity provider:
    - Agents get Firebase UIDs as their identity
    - Custom claims store tags, capabilities, permissions
    - Tokens can be revoked immediately
    """

    def __init__(self, service_account_path: Optional[str] = None, project_id: Optional[str] = None):
        """
        Initialize Firebase Admin SDK

        Args:
            service_account_path: Path to Firebase service account JSON file
            project_id: Firebase project ID (optional if using ADC)
        """
        self.initialized = False
        self.project_id = project_id or os.environ.get("FIREBASE_PROJECT_ID")

        if not FIREBASE_AVAILABLE:
            logger.error("Firebase Admin SDK not available")
            return

        # Check if already initialized
        try:
            firebase_admin.get_app()
            self.initialized = True
            logger.info("Firebase Admin SDK already initialized")
            return
        except ValueError:
            pass  # Not initialized yet

        # Determine credential source
        service_account_path = service_account_path or os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH")
        google_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

        try:
            if service_account_path and os.path.exists(service_account_path):
                # Use explicit service account file
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred)
                logger.info(f"Firebase initialized with service account: {service_account_path}")
            elif google_creds and os.path.exists(google_creds):
                # Use Application Default Credentials
                cred = credentials.Certificate(google_creds)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase initialized with Application Default Credentials")
            else:
                # Try default credentials (for GCE, Cloud Run, etc.)
                firebase_admin.initialize_app()
                logger.info("Firebase initialized with default credentials")

            self.initialized = True

        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            self.initialized = False

    def is_available(self) -> bool:
        """Check if Firebase is available and initialized"""
        return FIREBASE_AVAILABLE and self.initialized

    def get_status(self) -> Dict[str, Any]:
        """Get Firebase connection status"""
        return {
            "available": FIREBASE_AVAILABLE,
            "initialized": self.initialized,
            "project_id": self.project_id,
        }

    def create_agent_user(self, agent_id: str, display_name: Optional[str] = None) -> Optional[str]:
        """
        Create a Firebase user for an agent

        Args:
            agent_id: Unique agent identifier (becomes the UID)
            display_name: Optional display name

        Returns:
            Firebase UID if successful, None otherwise
        """
        if not self.is_available():
            logger.error("Firebase not available")
            return None

        try:
            # Create user with agent_id as UID
            user = auth.create_user(
                uid=agent_id,
                display_name=display_name or f"Agent: {agent_id}",
                disabled=False,
            )
            logger.info(f"Created Firebase user for agent: {agent_id}")
            return user.uid

        except auth.UidAlreadyExistsError:
            logger.info(f"Firebase user already exists for agent: {agent_id}")
            return agent_id

        except Exception as e:
            logger.error(f"Failed to create Firebase user for {agent_id}: {e}")
            return None

    def delete_agent_user(self, agent_id: str) -> bool:
        """Delete a Firebase user for an agent"""
        if not self.is_available():
            return False

        try:
            auth.delete_user(agent_id)
            logger.info(f"Deleted Firebase user: {agent_id}")
            return True
        except auth.UserNotFoundError:
            logger.warning(f"Firebase user not found: {agent_id}")
            return True  # Already deleted
        except Exception as e:
            logger.error(f"Failed to delete Firebase user {agent_id}: {e}")
            return False

    def mint_agent_token(self, agent_id: str, additional_claims: Optional[Dict] = None) -> Optional[str]:
        """
        Create a custom Firebase token for an agent

        The token includes custom claims that encode the agent's permissions,
        similar to Tailscale's tag-based access control.

        Args:
            agent_id: The agent's Firebase UID
            additional_claims: Extra claims to include in the token

        Returns:
            Custom token string if successful, None otherwise
        """
        if not self.is_available():
            logger.error("Firebase not available")
            return None

        try:
            # Custom claims are limited to 1000 bytes
            claims = additional_claims or {}

            # Add standard hAIveMind claims
            claims["iss"] = "haivemind"
            claims["iat"] = datetime.utcnow().isoformat()

            token = auth.create_custom_token(agent_id, claims)

            # Token is bytes in some SDK versions
            if isinstance(token, bytes):
                token = token.decode('utf-8')

            logger.info(f"Minted custom token for agent: {agent_id}")
            return token

        except Exception as e:
            logger.error(f"Failed to mint token for {agent_id}: {e}")
            return None

    def verify_agent_token(self, token: str, check_revoked: bool = True) -> TokenVerificationResult:
        """
        Verify a Firebase ID token and extract claims

        Args:
            token: Firebase ID token to verify
            check_revoked: Whether to check if token has been revoked

        Returns:
            TokenVerificationResult with verification status and claims
        """
        if not self.is_available():
            return TokenVerificationResult(valid=False, error="Firebase not available")

        try:
            decoded = auth.verify_id_token(token, check_revoked=check_revoked)

            # Extract agent claims
            claims = AgentClaims.from_dict(decoded)

            return TokenVerificationResult(
                valid=True,
                uid=decoded.get("uid"),
                claims=claims,
            )

        except auth.RevokedIdTokenError:
            return TokenVerificationResult(valid=False, error="Token revoked", revoked=True)

        except auth.ExpiredIdTokenError:
            return TokenVerificationResult(valid=False, error="Token expired")

        except auth.InvalidIdTokenError as e:
            return TokenVerificationResult(valid=False, error=f"Invalid token: {e}")

        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return TokenVerificationResult(valid=False, error=str(e))

    def set_agent_claims(self, agent_id: str, claims: AgentClaims) -> bool:
        """
        Set custom claims for an agent

        Custom claims are embedded in ID tokens and can be used for
        authorization decisions without database lookups.

        Args:
            agent_id: The agent's Firebase UID
            claims: AgentClaims object with permissions/tags

        Returns:
            True if successful
        """
        if not self.is_available():
            return False

        try:
            auth.set_custom_user_claims(agent_id, claims.to_dict())
            logger.info(f"Set custom claims for agent: {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to set claims for {agent_id}: {e}")
            return False

    def get_agent_claims(self, agent_id: str) -> Optional[AgentClaims]:
        """Get current custom claims for an agent"""
        if not self.is_available():
            return None

        try:
            user = auth.get_user(agent_id)
            if user.custom_claims:
                return AgentClaims.from_dict(user.custom_claims)
            return None

        except auth.UserNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Failed to get claims for {agent_id}: {e}")
            return None

    def update_agent_tags(self, agent_id: str, tags: List[str], append: bool = False) -> bool:
        """
        Update an agent's tags (Tailscale-style)

        Args:
            agent_id: The agent's Firebase UID
            tags: List of tags (e.g., ["tag:elasticsearch", "tag:production"])
            append: If True, add to existing tags; if False, replace

        Returns:
            True if successful
        """
        if not self.is_available():
            return False

        try:
            current = self.get_agent_claims(agent_id)
            if current is None:
                current = AgentClaims(agent_type="unknown", machine_id="unknown")

            if append:
                # Merge tags
                existing = set(current.tags)
                existing.update(tags)
                current.tags = list(existing)
            else:
                current.tags = tags

            return self.set_agent_claims(agent_id, current)

        except Exception as e:
            logger.error(f"Failed to update tags for {agent_id}: {e}")
            return False

    def update_agent_capabilities(self, agent_id: str, capabilities: List[str], append: bool = False) -> bool:
        """Update an agent's capabilities"""
        if not self.is_available():
            return False

        try:
            current = self.get_agent_claims(agent_id)
            if current is None:
                current = AgentClaims(agent_type="unknown", machine_id="unknown")

            if append:
                existing = set(current.capabilities)
                existing.update(capabilities)
                current.capabilities = list(existing)
            else:
                current.capabilities = capabilities

            return self.set_agent_claims(agent_id, current)

        except Exception as e:
            logger.error(f"Failed to update capabilities for {agent_id}: {e}")
            return False

    def revoke_agent_tokens(self, agent_id: str) -> bool:
        """
        Revoke all refresh tokens for an agent

        This immediately invalidates any existing sessions.
        ID tokens remain valid until their natural expiration (1 hour),
        but check_revoked=True catches revoked tokens.

        Args:
            agent_id: The agent's Firebase UID

        Returns:
            True if successful
        """
        if not self.is_available():
            return False

        try:
            auth.revoke_refresh_tokens(agent_id)
            logger.info(f"Revoked tokens for agent: {agent_id}")
            return True

        except auth.UserNotFoundError:
            logger.warning(f"Agent not found for revocation: {agent_id}")
            return False

        except Exception as e:
            logger.error(f"Failed to revoke tokens for {agent_id}: {e}")
            return False

    def disable_agent(self, agent_id: str) -> bool:
        """Disable an agent's Firebase account"""
        if not self.is_available():
            return False

        try:
            auth.update_user(agent_id, disabled=True)
            logger.info(f"Disabled agent: {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to disable agent {agent_id}: {e}")
            return False

    def enable_agent(self, agent_id: str) -> bool:
        """Enable a previously disabled agent"""
        if not self.is_available():
            return False

        try:
            auth.update_user(agent_id, disabled=False)
            logger.info(f"Enabled agent: {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to enable agent {agent_id}: {e}")
            return False

    def list_agents(self, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        List all registered agents

        Returns:
            List of agent info dictionaries
        """
        if not self.is_available():
            return []

        try:
            agents = []
            page = auth.list_users()

            for user in page.iterate_all():
                if len(agents) >= max_results:
                    break

                agents.append({
                    "uid": user.uid,
                    "display_name": user.display_name,
                    "disabled": user.disabled,
                    "custom_claims": user.custom_claims or {},
                    "created_at": user.user_metadata.creation_timestamp if user.user_metadata else None,
                    "last_sign_in": user.user_metadata.last_sign_in_timestamp if user.user_metadata else None,
                })

            return agents

        except Exception as e:
            logger.error(f"Failed to list agents: {e}")
            return []


# Singleton instance
_firebase_auth: Optional[FirebaseAgentAuth] = None


def get_firebase_auth() -> FirebaseAgentAuth:
    """Get or create the Firebase auth singleton"""
    global _firebase_auth
    if _firebase_auth is None:
        _firebase_auth = FirebaseAgentAuth()
    return _firebase_auth


def initialize_firebase(service_account_path: Optional[str] = None, project_id: Optional[str] = None) -> FirebaseAgentAuth:
    """Initialize Firebase with explicit configuration"""
    global _firebase_auth
    _firebase_auth = FirebaseAgentAuth(service_account_path, project_id)
    return _firebase_auth
