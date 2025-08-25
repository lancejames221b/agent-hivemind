"""
Role-Based Access Control and Authentication System
Enterprise-grade access control for the credential vault.

Author: Lance James, Unit 221B
"""

import asyncio
import logging
import secrets
import hashlib
import json
import jwt
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import bcrypt
import pyotp
import qrcode
from io import BytesIO
import base64
import redis
import asyncpg


class UserRole(Enum):
    """User roles in the system"""
    SUPER_ADMIN = "super_admin"
    ORGANIZATION_ADMIN = "organization_admin"
    ENVIRONMENT_ADMIN = "environment_admin"
    PROJECT_ADMIN = "project_admin"
    SERVICE_ADMIN = "service_admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"
    AGENT = "agent"
    SECURITY_ADMIN = "security_admin"
    AUDIT_ADMIN = "audit_admin"


class Permission(Enum):
    """Granular permissions"""
    CREATE_CREDENTIAL = "create_credential"
    READ_CREDENTIAL = "read_credential"
    UPDATE_CREDENTIAL = "update_credential"
    DELETE_CREDENTIAL = "delete_credential"
    ROTATE_CREDENTIAL = "rotate_credential"
    SHARE_CREDENTIAL = "share_credential"
    EXPORT_CREDENTIAL = "export_credential"
    
    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"
    MANAGE_ORGANIZATIONS = "manage_organizations"
    MANAGE_ENVIRONMENTS = "manage_environments"
    MANAGE_PROJECTS = "manage_projects"
    MANAGE_SERVICES = "manage_services"
    
    VIEW_AUDIT_LOGS = "view_audit_logs"
    MANAGE_AUDIT_LOGS = "manage_audit_logs"
    VIEW_SECURITY_EVENTS = "view_security_events"
    MANAGE_SECURITY_EVENTS = "manage_security_events"
    
    EMERGENCY_ACCESS = "emergency_access"
    SYSTEM_ADMIN = "system_admin"


class MFAMethod(Enum):
    """Multi-factor authentication methods"""
    TOTP = "totp"
    HOTP = "hotp"
    SMS = "sms"
    EMAIL = "email"
    WEBAUTHN = "webauthn"
    PUSH = "push"


@dataclass
class RolePermissions:
    """Role-based permissions mapping"""
    role: UserRole
    permissions: Set[Permission]
    scope_restrictions: Dict[str, Any] = field(default_factory=dict)
    conditions: List[str] = field(default_factory=list)


@dataclass
class User:
    """User data structure"""
    user_id: str
    email: str
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    password_hash: Optional[str]
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    mfa_enabled: bool = False
    mfa_secret: Optional[str] = None
    mfa_backup_codes: List[str] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserRoleAssignment:
    """User role assignment with scope"""
    user_id: str
    role: UserRole
    organization_id: Optional[str] = None
    environment_id: Optional[str] = None
    project_id: Optional[str] = None
    service_id: Optional[str] = None
    granted_by: str = ""
    granted_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    is_active: bool = True


@dataclass
class AuthenticationSession:
    """User authentication session"""
    session_id: str
    user_id: str
    session_token: str
    security_level: str = "standard"
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(hours=8))
    last_activity: datetime = field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    mfa_verified: bool = False
    is_active: bool = True


class PasswordPolicy:
    """Password policy enforcement"""
    
    def __init__(self, min_length: int = 12, require_uppercase: bool = True,
                 require_lowercase: bool = True, require_numbers: bool = True,
                 require_special_chars: bool = True, max_age_days: int = 90,
                 history_count: int = 12):
        self.min_length = min_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_numbers = require_numbers
        self.require_special_chars = require_special_chars
        self.max_age_days = max_age_days
        self.history_count = history_count
        self.special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    def validate_password(self, password: str) -> Tuple[bool, List[str]]:
        """Validate password against policy"""
        errors = []
        
        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters long")
        
        if self.require_uppercase and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if self.require_lowercase and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if self.require_numbers and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one number")
        
        if self.require_special_chars and not any(c in self.special_chars for c in password):
            errors.append("Password must contain at least one special character")
        
        return len(errors) == 0, errors
    
    def generate_secure_password(self, length: int = None) -> str:
        """Generate a secure password that meets policy requirements"""
        if length is None:
            length = max(self.min_length, 16)
        
        import string
        import random
        
        # Ensure we have at least one character from each required category
        chars = []
        if self.require_lowercase:
            chars.append(random.choice(string.ascii_lowercase))
        if self.require_uppercase:
            chars.append(random.choice(string.ascii_uppercase))
        if self.require_numbers:
            chars.append(random.choice(string.digits))
        if self.require_special_chars:
            chars.append(random.choice(self.special_chars))
        
        # Fill the rest with random characters from all categories
        all_chars = string.ascii_letters + string.digits + self.special_chars
        for _ in range(length - len(chars)):
            chars.append(random.choice(all_chars))
        
        # Shuffle the characters
        random.shuffle(chars)
        return ''.join(chars)


class RoleBasedAccessControl:
    """Role-based access control system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.role_permissions = self._initialize_role_permissions()
    
    def _initialize_role_permissions(self) -> Dict[UserRole, RolePermissions]:
        """Initialize role-permission mappings"""
        return {
            UserRole.SUPER_ADMIN: RolePermissions(
                role=UserRole.SUPER_ADMIN,
                permissions={
                    Permission.CREATE_CREDENTIAL, Permission.READ_CREDENTIAL,
                    Permission.UPDATE_CREDENTIAL, Permission.DELETE_CREDENTIAL,
                    Permission.ROTATE_CREDENTIAL, Permission.SHARE_CREDENTIAL,
                    Permission.EXPORT_CREDENTIAL, Permission.MANAGE_USERS,
                    Permission.MANAGE_ROLES, Permission.MANAGE_ORGANIZATIONS,
                    Permission.MANAGE_ENVIRONMENTS, Permission.MANAGE_PROJECTS,
                    Permission.MANAGE_SERVICES, Permission.VIEW_AUDIT_LOGS,
                    Permission.MANAGE_AUDIT_LOGS, Permission.VIEW_SECURITY_EVENTS,
                    Permission.MANAGE_SECURITY_EVENTS, Permission.EMERGENCY_ACCESS,
                    Permission.SYSTEM_ADMIN
                }
            ),
            
            UserRole.ORGANIZATION_ADMIN: RolePermissions(
                role=UserRole.ORGANIZATION_ADMIN,
                permissions={
                    Permission.CREATE_CREDENTIAL, Permission.READ_CREDENTIAL,
                    Permission.UPDATE_CREDENTIAL, Permission.DELETE_CREDENTIAL,
                    Permission.ROTATE_CREDENTIAL, Permission.SHARE_CREDENTIAL,
                    Permission.MANAGE_USERS, Permission.MANAGE_ROLES,
                    Permission.MANAGE_ENVIRONMENTS, Permission.MANAGE_PROJECTS,
                    Permission.MANAGE_SERVICES, Permission.VIEW_AUDIT_LOGS,
                    Permission.VIEW_SECURITY_EVENTS
                },
                scope_restrictions={"organization_scoped": True}
            ),
            
            UserRole.ENVIRONMENT_ADMIN: RolePermissions(
                role=UserRole.ENVIRONMENT_ADMIN,
                permissions={
                    Permission.CREATE_CREDENTIAL, Permission.READ_CREDENTIAL,
                    Permission.UPDATE_CREDENTIAL, Permission.DELETE_CREDENTIAL,
                    Permission.ROTATE_CREDENTIAL, Permission.SHARE_CREDENTIAL,
                    Permission.MANAGE_USERS, Permission.MANAGE_PROJECTS,
                    Permission.MANAGE_SERVICES, Permission.VIEW_AUDIT_LOGS
                },
                scope_restrictions={"environment_scoped": True}
            ),
            
            UserRole.PROJECT_ADMIN: RolePermissions(
                role=UserRole.PROJECT_ADMIN,
                permissions={
                    Permission.CREATE_CREDENTIAL, Permission.READ_CREDENTIAL,
                    Permission.UPDATE_CREDENTIAL, Permission.DELETE_CREDENTIAL,
                    Permission.ROTATE_CREDENTIAL, Permission.SHARE_CREDENTIAL,
                    Permission.MANAGE_SERVICES, Permission.VIEW_AUDIT_LOGS
                },
                scope_restrictions={"project_scoped": True}
            ),
            
            UserRole.SERVICE_ADMIN: RolePermissions(
                role=UserRole.SERVICE_ADMIN,
                permissions={
                    Permission.CREATE_CREDENTIAL, Permission.READ_CREDENTIAL,
                    Permission.UPDATE_CREDENTIAL, Permission.ROTATE_CREDENTIAL,
                    Permission.SHARE_CREDENTIAL, Permission.VIEW_AUDIT_LOGS
                },
                scope_restrictions={"service_scoped": True},
                conditions=["limited_delete"]
            ),
            
            UserRole.DEVELOPER: RolePermissions(
                role=UserRole.DEVELOPER,
                permissions={
                    Permission.READ_CREDENTIAL, Permission.VIEW_AUDIT_LOGS
                },
                scope_restrictions={"project_scoped": True},
                conditions=["limited_create", "no_production_access"]
            ),
            
            UserRole.VIEWER: RolePermissions(
                role=UserRole.VIEWER,
                permissions={
                    Permission.READ_CREDENTIAL, Permission.VIEW_AUDIT_LOGS
                },
                scope_restrictions={"read_only": True}
            ),
            
            UserRole.AGENT: RolePermissions(
                role=UserRole.AGENT,
                permissions={
                    Permission.READ_CREDENTIAL
                },
                scope_restrictions={"api_only": True, "service_scoped": True}
            ),
            
            UserRole.SECURITY_ADMIN: RolePermissions(
                role=UserRole.SECURITY_ADMIN,
                permissions={
                    Permission.READ_CREDENTIAL, Permission.VIEW_AUDIT_LOGS,
                    Permission.MANAGE_AUDIT_LOGS, Permission.VIEW_SECURITY_EVENTS,
                    Permission.MANAGE_SECURITY_EVENTS, Permission.EMERGENCY_ACCESS
                }
            ),
            
            UserRole.AUDIT_ADMIN: RolePermissions(
                role=UserRole.AUDIT_ADMIN,
                permissions={
                    Permission.VIEW_AUDIT_LOGS, Permission.MANAGE_AUDIT_LOGS,
                    Permission.VIEW_SECURITY_EVENTS
                }
            )
        }
    
    def get_user_permissions(self, user_roles: List[UserRoleAssignment]) -> Set[Permission]:
        """Get combined permissions for all user roles"""
        permissions = set()
        
        for role_assignment in user_roles:
            if role_assignment.is_active and (
                role_assignment.expires_at is None or 
                role_assignment.expires_at > datetime.utcnow()
            ):
                role_perms = self.role_permissions.get(role_assignment.role)
                if role_perms:
                    permissions.update(role_perms.permissions)
        
        return permissions
    
    def check_permission(self, user_roles: List[UserRoleAssignment], 
                        required_permission: Permission,
                        resource_context: Dict[str, Any] = None) -> bool:
        """Check if user has required permission for a resource"""
        user_permissions = self.get_user_permissions(user_roles)
        
        if required_permission not in user_permissions:
            return False
        
        # Check scope restrictions
        if resource_context:
            for role_assignment in user_roles:
                if not role_assignment.is_active:
                    continue
                
                role_perms = self.role_permissions.get(role_assignment.role)
                if not role_perms or required_permission not in role_perms.permissions:
                    continue
                
                # Check scope restrictions
                if self._check_scope_restrictions(role_assignment, role_perms, resource_context):
                    return True
            
            return False
        
        return True
    
    def _check_scope_restrictions(self, role_assignment: UserRoleAssignment,
                                role_perms: RolePermissions,
                                resource_context: Dict[str, Any]) -> bool:
        """Check if role assignment scope allows access to resource"""
        restrictions = role_perms.scope_restrictions
        
        if restrictions.get("organization_scoped"):
            if (role_assignment.organization_id and 
                resource_context.get("organization_id") != role_assignment.organization_id):
                return False
        
        if restrictions.get("environment_scoped"):
            if (role_assignment.environment_id and 
                resource_context.get("environment_id") != role_assignment.environment_id):
                return False
        
        if restrictions.get("project_scoped"):
            if (role_assignment.project_id and 
                resource_context.get("project_id") != role_assignment.project_id):
                return False
        
        if restrictions.get("service_scoped"):
            if (role_assignment.service_id and 
                resource_context.get("service_id") != role_assignment.service_id):
                return False
        
        return True


class MultiFactorAuthentication:
    """Multi-factor authentication system"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.logger = logging.getLogger(__name__)
    
    def generate_totp_secret(self) -> str:
        """Generate a new TOTP secret"""
        return pyotp.random_base32()
    
    def generate_qr_code(self, user_email: str, secret: str, issuer: str = "hAIveMind Vault") -> str:
        """Generate QR code for TOTP setup"""
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user_email,
            issuer_name=issuer
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        
        return base64.b64encode(buffer.getvalue()).decode()
    
    def verify_totp(self, secret: str, token: str, window: int = 1) -> bool:
        """Verify TOTP token"""
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=window)
    
    def generate_backup_codes(self, count: int = 10) -> List[str]:
        """Generate backup codes for MFA recovery"""
        codes = []
        for _ in range(count):
            code = secrets.token_hex(4).upper()
            codes.append(f"{code[:4]}-{code[4:]}")
        return codes
    
    async def send_sms_code(self, phone_number: str, code: str) -> bool:
        """Send SMS verification code (placeholder implementation)"""
        # In production, integrate with SMS service like Twilio
        self.logger.info(f"Would send SMS code {code} to {phone_number}")
        
        # Store code in Redis with expiration
        await self.redis.setex(f"sms_code:{phone_number}", 300, code)
        return True
    
    async def verify_sms_code(self, phone_number: str, code: str) -> bool:
        """Verify SMS code"""
        stored_code = await self.redis.get(f"sms_code:{phone_number}")
        if stored_code and stored_code.decode() == code:
            await self.redis.delete(f"sms_code:{phone_number}")
            return True
        return False


class AuthenticationManager:
    """Main authentication and session management"""
    
    def __init__(self, database_url: str, redis_client: redis.Redis, 
                 jwt_secret: str, password_policy: PasswordPolicy = None):
        self.database_url = database_url
        self.redis = redis_client
        self.jwt_secret = jwt_secret
        self.password_policy = password_policy or PasswordPolicy()
        self.rbac = RoleBasedAccessControl()
        self.mfa = MultiFactorAuthentication(redis_client)
        self.logger = logging.getLogger(__name__)
        self.pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self) -> bool:
        """Initialize authentication manager"""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=5,
                max_size=20,
                command_timeout=30
            )
            self.logger.info("Authentication manager initialized")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize authentication manager: {str(e)}")
            return False
    
    async def close(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    async def create_user(self, email: str, password: str, username: str = None,
                         first_name: str = None, last_name: str = None) -> Optional[str]:
        """Create a new user"""
        try:
            # Validate password
            is_valid, errors = self.password_policy.validate_password(password)
            if not is_valid:
                self.logger.warning(f"Password validation failed: {errors}")
                return None
            
            # Hash password
            password_hash = self.hash_password(password)
            
            # Generate user ID
            user_id = secrets.token_hex(16)
            
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO users (
                        id, email, username, first_name, last_name, password_hash
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                """, user_id, email, username, first_name, last_name, password_hash)
            
            self.logger.info(f"Created user {email} with ID {user_id}")
            return user_id
            
        except Exception as e:
            self.logger.error(f"Failed to create user {email}: {str(e)}")
            return None
    
    async def authenticate_user(self, email: str, password: str, 
                              ip_address: str = None, user_agent: str = None) -> Optional[Dict[str, Any]]:
        """Authenticate user with email and password"""
        try:
            async with self.pool.acquire() as conn:
                user_row = await conn.fetchrow("""
                    SELECT id, email, password_hash, is_active, is_verified,
                           failed_login_attempts, locked_until, mfa_enabled, mfa_secret
                    FROM users WHERE email = $1
                """, email)
                
                if not user_row:
                    self.logger.warning(f"Authentication failed: user {email} not found")
                    return None
                
                # Check if account is locked
                if user_row['locked_until'] and user_row['locked_until'] > datetime.utcnow():
                    self.logger.warning(f"Authentication failed: user {email} is locked")
                    return None
                
                # Check if account is active and verified
                if not user_row['is_active'] or not user_row['is_verified']:
                    self.logger.warning(f"Authentication failed: user {email} is inactive or unverified")
                    return None
                
                # Verify password
                if not self.verify_password(password, user_row['password_hash']):
                    # Increment failed attempts
                    failed_attempts = user_row['failed_login_attempts'] + 1
                    locked_until = None
                    
                    if failed_attempts >= 5:  # Lock after 5 failed attempts
                        locked_until = datetime.utcnow() + timedelta(minutes=30)
                    
                    await conn.execute("""
                        UPDATE users 
                        SET failed_login_attempts = $1, locked_until = $2
                        WHERE id = $3
                    """, failed_attempts, locked_until, user_row['id'])
                    
                    self.logger.warning(f"Authentication failed: invalid password for {email}")
                    return None
                
                # Reset failed attempts on successful authentication
                await conn.execute("""
                    UPDATE users 
                    SET failed_login_attempts = 0, locked_until = NULL, last_login = NOW()
                    WHERE id = $1
                """, user_row['id'])
                
                return {
                    'user_id': user_row['id'],
                    'email': user_row['email'],
                    'mfa_enabled': user_row['mfa_enabled'],
                    'mfa_required': user_row['mfa_enabled']
                }
                
        except Exception as e:
            self.logger.error(f"Authentication error for {email}: {str(e)}")
            return None
    
    async def create_session(self, user_id: str, security_level: str = "standard",
                           ip_address: str = None, user_agent: str = None,
                           mfa_verified: bool = False) -> Optional[AuthenticationSession]:
        """Create a new authentication session"""
        try:
            session_id = secrets.token_hex(16)
            session_token = jwt.encode({
                'session_id': session_id,
                'user_id': user_id,
                'security_level': security_level,
                'mfa_verified': mfa_verified,
                'iat': datetime.utcnow().timestamp(),
                'exp': (datetime.utcnow() + timedelta(hours=8)).timestamp()
            }, self.jwt_secret, algorithm='HS256')
            
            session = AuthenticationSession(
                session_id=session_id,
                user_id=user_id,
                session_token=session_token,
                security_level=security_level,
                ip_address=ip_address,
                user_agent=user_agent,
                mfa_verified=mfa_verified
            )
            
            # Store session in database
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO security_sessions (
                        id, user_id, session_token, security_level,
                        expires_at, ip_address, user_agent, mfa_verified
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, session.session_id, session.user_id, session.session_token,
                    session.security_level, session.expires_at, session.ip_address,
                    session.user_agent, session.mfa_verified)
            
            # Cache session in Redis
            await self.redis.setex(
                f"session:{session_id}",
                int((session.expires_at - datetime.utcnow()).total_seconds()),
                json.dumps({
                    'user_id': user_id,
                    'security_level': security_level,
                    'mfa_verified': mfa_verified
                })
            )
            
            self.logger.info(f"Created session {session_id} for user {user_id}")
            return session
            
        except Exception as e:
            self.logger.error(f"Failed to create session for user {user_id}: {str(e)}")
            return None
    
    async def validate_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Validate and decode session token"""
        try:
            # Decode JWT token
            payload = jwt.decode(session_token, self.jwt_secret, algorithms=['HS256'])
            session_id = payload['session_id']
            
            # Check Redis cache first
            cached_session = await self.redis.get(f"session:{session_id}")
            if cached_session:
                session_data = json.loads(cached_session)
                return {
                    'session_id': session_id,
                    'user_id': session_data['user_id'],
                    'security_level': session_data['security_level'],
                    'mfa_verified': session_data['mfa_verified'],
                    'valid': True
                }
            
            # Check database if not in cache
            async with self.pool.acquire() as conn:
                session_row = await conn.fetchrow("""
                    SELECT user_id, security_level, mfa_verified, expires_at, is_active
                    FROM security_sessions
                    WHERE id = $1 AND session_token = $2
                """, session_id, session_token)
                
                if (session_row and session_row['is_active'] and 
                    session_row['expires_at'] > datetime.utcnow()):
                    
                    # Update last activity
                    await conn.execute("""
                        UPDATE security_sessions SET last_activity = NOW() WHERE id = $1
                    """, session_id)
                    
                    return {
                        'session_id': session_id,
                        'user_id': session_row['user_id'],
                        'security_level': session_row['security_level'],
                        'mfa_verified': session_row['mfa_verified'],
                        'valid': True
                    }
            
            return None
            
        except jwt.ExpiredSignatureError:
            self.logger.warning("Session token expired")
            return None
        except jwt.InvalidTokenError:
            self.logger.warning("Invalid session token")
            return None
        except Exception as e:
            self.logger.error(f"Session validation error: {str(e)}")
            return None
    
    async def revoke_session(self, session_id: str) -> bool:
        """Revoke a session"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE security_sessions 
                    SET is_active = false, revoked_at = NOW()
                    WHERE id = $1
                """, session_id)
            
            # Remove from Redis cache
            await self.redis.delete(f"session:{session_id}")
            
            self.logger.info(f"Revoked session {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to revoke session {session_id}: {str(e)}")
            return False
    
    async def get_user_roles(self, user_id: str) -> List[UserRoleAssignment]:
        """Get all active roles for a user"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT user_id, role, organization_id, environment_id, 
                           project_id, service_id, granted_by, granted_at, 
                           expires_at, is_active
                    FROM user_roles
                    WHERE user_id = $1 AND is_active = true
                    AND (expires_at IS NULL OR expires_at > NOW())
                """, user_id)
                
                roles = []
                for row in rows:
                    roles.append(UserRoleAssignment(
                        user_id=row['user_id'],
                        role=UserRole(row['role']),
                        organization_id=row['organization_id'],
                        environment_id=row['environment_id'],
                        project_id=row['project_id'],
                        service_id=row['service_id'],
                        granted_by=row['granted_by'],
                        granted_at=row['granted_at'],
                        expires_at=row['expires_at'],
                        is_active=row['is_active']
                    ))
                
                return roles
                
        except Exception as e:
            self.logger.error(f"Failed to get user roles for {user_id}: {str(e)}")
            return []
    
    async def check_user_permission(self, user_id: str, permission: Permission,
                                  resource_context: Dict[str, Any] = None) -> bool:
        """Check if user has specific permission"""
        user_roles = await self.get_user_roles(user_id)
        return self.rbac.check_permission(user_roles, permission, resource_context)


# Example usage
async def main():
    """Example usage of the access control system"""
    import redis.asyncio as redis
    
    # Configuration
    database_url = "postgresql://vault:password@localhost/vault"
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    jwt_secret = "your-jwt-secret-key-here"
    
    # Initialize authentication manager
    auth_manager = AuthenticationManager(database_url, redis_client, jwt_secret)
    
    if await auth_manager.initialize():
        print("✅ Authentication manager initialized")
        
        # Create a test user
        user_id = await auth_manager.create_user(
            email="admin@company.com",
            password="SecurePassword123!",
            username="admin",
            first_name="System",
            last_name="Administrator"
        )
        
        if user_id:
            print(f"✅ Created user with ID: {user_id}")
            
            # Authenticate user
            auth_result = await auth_manager.authenticate_user(
                email="admin@company.com",
                password="SecurePassword123!",
                ip_address="192.168.1.100"
            )
            
            if auth_result:
                print("✅ User authenticated successfully")
                
                # Create session
                session = await auth_manager.create_session(
                    user_id=auth_result['user_id'],
                    ip_address="192.168.1.100"
                )
                
                if session:
                    print(f"✅ Session created: {session.session_id}")
                    
                    # Validate session
                    session_data = await auth_manager.validate_session(session.session_token)
                    if session_data and session_data['valid']:
                        print("✅ Session validated successfully")
                    else:
                        print("❌ Session validation failed")
                else:
                    print("❌ Failed to create session")
            else:
                print("❌ Authentication failed")
        else:
            print("❌ Failed to create user")
        
        await auth_manager.close()
    else:
        print("❌ Failed to initialize authentication manager")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())