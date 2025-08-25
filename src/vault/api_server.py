"""
REST API Server for Enterprise Credential Vault
FastAPI-based REST API with comprehensive security and enterprise features.

Author: Lance James, Unit 221B
"""

import asyncio
import logging
import json
import secrets
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, Security, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, EmailStr
from contextlib import asynccontextmanager
import redis.asyncio as redis
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .core_vault import CoreVault, CredentialType, RiskLevel, EncryptionConfig
from .access_control import AuthenticationManager, Permission, UserRole, PasswordPolicy
from .enterprise_integration import EnterpriseIntegration, ComplianceStandard, LDAPConfig
from .enhanced_haivemind_analytics import EnhancedHAIveMindIntegration
from ..memory_server import MemoryMCPServer


# Pydantic models for API requests/responses
class CredentialCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    credential_type: CredentialType
    credential_data: Dict[str, Any]
    organization_id: str
    environment_id: Optional[str] = None
    project_id: Optional[str] = None
    service_id: Optional[str] = None
    risk_level: RiskLevel = RiskLevel.MEDIUM
    tags: List[str] = Field(default_factory=list)
    compliance_labels: List[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None
    rotation_interval_days: int = Field(90, ge=1, le=3650)
    auto_rotate: bool = False


class CredentialResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    credential_type: CredentialType
    organization_id: str
    environment_id: Optional[str]
    project_id: Optional[str]
    service_id: Optional[str]
    owner_id: str
    created_at: datetime
    updated_at: datetime
    last_accessed: Optional[datetime]
    expires_at: Optional[datetime]
    risk_level: RiskLevel
    tags: List[str]
    compliance_labels: List[str]
    access_count: int


class CredentialDataResponse(BaseModel):
    credential_data: Dict[str, Any]
    metadata: Dict[str, Any]


class UserCreateRequest(BaseModel):
    email: EmailStr
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    id: str
    email: str
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime]
    mfa_enabled: bool


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    mfa_token: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
    session_id: str


class RoleAssignmentRequest(BaseModel):
    user_id: str
    role: UserRole
    organization_id: Optional[str] = None
    environment_id: Optional[str] = None
    project_id: Optional[str] = None
    service_id: Optional[str] = None
    expires_at: Optional[datetime] = None


class ComplianceReportRequest(BaseModel):
    standard: ComplianceStandard
    start_date: datetime
    end_date: datetime
    organization_id: Optional[str] = None
    environment_id: Optional[str] = None


class AuditExportRequest(BaseModel):
    start_date: datetime
    end_date: datetime
    format: str = Field("csv", regex="^(csv|json)$")
    event_types: Optional[List[str]] = None
    user_ids: Optional[List[str]] = None


# Global variables for dependency injection
vault_core: Optional[CoreVault] = None
auth_manager: Optional[AuthenticationManager] = None
enterprise_integration: Optional[EnterpriseIntegration] = None
haivemind_integration: Optional[EnhancedHAIveMindIntegration] = None
redis_client: Optional[redis.Redis] = None

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# Security scheme
security = HTTPBearer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global vault_core, auth_manager, enterprise_integration, haivemind_integration, redis_client
    
    try:
        # Initialize Redis
        redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )
        
        # Initialize core components
        database_url = "postgresql://vault:password@localhost/vault"
        jwt_secret = "your-jwt-secret-key-here"
        
        # Initialize vault core
        vault_core = CoreVault(database_url, redis_client)
        await vault_core.initialize()
        
        # Initialize authentication manager
        password_policy = PasswordPolicy(min_length=12, require_special_chars=True)
        auth_manager = AuthenticationManager(database_url, redis_client, jwt_secret, password_policy)
        await auth_manager.initialize()
        
        # Initialize enterprise integration
        enterprise_integration = EnterpriseIntegration(database_url, redis_client)
        await enterprise_integration.initialize()
        
        # Initialize hAIveMind integration
        config = {'machine_id': 'vault-api-server'}
        memory_server = MemoryMCPServer()  # This would be properly initialized
        haivemind_integration = EnhancedHAIveMindIntegration(config, redis_client, memory_server)
        await haivemind_integration.initialize()
        
        logging.info("Vault API server initialized successfully")
        yield
        
    except Exception as e:
        logging.error(f"Failed to initialize vault API server: {str(e)}")
        raise
    finally:
        # Cleanup
        if vault_core:
            await vault_core.close()
        if auth_manager:
            await auth_manager.close()
        if enterprise_integration:
            await enterprise_integration.close()
        if redis_client:
            await redis_client.close()


# Create FastAPI app
app = FastAPI(
    title="hAIveMind Enterprise Credential Vault API",
    description="Secure, enterprise-grade credential management with hAIveMind integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(SlowAPIMiddleware)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://vault.haivemind.local", "https://admin.haivemind.local"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["vault.haivemind.local", "*.haivemind.local", "localhost"]
)


# Security dependencies
async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, Any]:
    """Get current authenticated user"""
    try:
        session_data = await auth_manager.validate_session(credentials.credentials)
        if not session_data or not session_data.get('valid'):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return session_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_permission(permission: Permission):
    """Dependency factory for permission checking"""
    async def check_permission(
        current_user: Dict[str, Any] = Depends(get_current_user),
        request: Request = None
    ):
        user_id = current_user['user_id']
        
        # Get resource context from request
        resource_context = {}
        if hasattr(request, 'path_params'):
            resource_context.update(request.path_params)
        
        # Check permission
        has_permission = await auth_manager.check_user_permission(
            user_id, permission, resource_context
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: {permission.value} required"
            )
        
        return current_user
    
    return check_permission


# Audit logging decorator
async def log_api_access(request: Request, response: Response, current_user: Dict[str, Any] = None):
    """Log API access for audit purposes"""
    try:
        if vault_core and current_user:
            await vault_core.database.log_audit_event(
                event_type="api_access",
                user_id=current_user.get('user_id'),
                credential_id=None,
                action=f"{request.method} {request.url.path}",
                result="success" if response.status_code < 400 else "failure",
                ip_address=request.client.host,
                user_agent=request.headers.get('user-agent'),
                metadata={
                    'status_code': response.status_code,
                    'path_params': dict(request.path_params),
                    'query_params': dict(request.query_params)
                }
            )
    except Exception as e:
        logging.error(f"Failed to log API access: {str(e)}")


# Health check endpoint
@app.get("/health", tags=["System"])
@limiter.limit("100/minute")
async def health_check(request: Request):
    """Health check endpoint"""
    try:
        # Check database connectivity
        if vault_core and vault_core.database.pool:
            async with vault_core.database.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
        
        # Check Redis connectivity
        if redis_client:
            await redis_client.ping()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "components": {
                "database": "healthy",
                "redis": "healthy",
                "authentication": "healthy" if auth_manager else "unavailable",
                "enterprise": "healthy" if enterprise_integration else "unavailable",
                "haivemind": "healthy" if haivemind_integration else "unavailable"
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


# Authentication endpoints
@app.post("/auth/login", response_model=LoginResponse, tags=["Authentication"])
@limiter.limit("10/minute")
async def login(request: Request, login_data: LoginRequest):
    """Authenticate user and create session"""
    try:
        # Authenticate user
        auth_result = await auth_manager.authenticate_user(
            email=login_data.email,
            password=login_data.password,
            ip_address=request.client.host,
            user_agent=request.headers.get('user-agent')
        )
        
        if not auth_result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Check MFA if required
        if auth_result.get('mfa_required') and not login_data.mfa_token:
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail="MFA token required",
                headers={"X-MFA-Required": "true"}
            )
        
        mfa_verified = False
        if login_data.mfa_token and auth_result.get('mfa_enabled'):
            # Verify MFA token (implementation depends on MFA method)
            mfa_verified = True  # Placeholder
        
        # Create session
        session = await auth_manager.create_session(
            user_id=auth_result['user_id'],
            ip_address=request.client.host,
            user_agent=request.headers.get('user-agent'),
            mfa_verified=mfa_verified
        )
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create session"
            )
        
        # Get user details (mock implementation)
        user = UserResponse(
            id=auth_result['user_id'],
            email=auth_result['email'],
            username=None,
            first_name=None,
            last_name=None,
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
            last_login=datetime.utcnow(),
            mfa_enabled=auth_result.get('mfa_enabled', False)
        )
        
        return LoginResponse(
            access_token=session.session_token,
            expires_in=int((session.expires_at - datetime.utcnow()).total_seconds()),
            user=user,
            session_id=session.session_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )


@app.post("/auth/logout", tags=["Authentication"])
@limiter.limit("30/minute")
async def logout(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Logout user and revoke session"""
    try:
        session_id = current_user.get('session_id')
        if session_id:
            await auth_manager.revoke_session(session_id)
        
        await log_api_access(request, Response(status_code=200), current_user)
        
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        logging.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


# User management endpoints
@app.post("/users", response_model=UserResponse, tags=["User Management"])
@limiter.limit("10/minute")
async def create_user(
    request: Request,
    user_data: UserCreateRequest,
    current_user: Dict[str, Any] = Depends(require_permission(Permission.MANAGE_USERS))
):
    """Create a new user"""
    try:
        user_id = await auth_manager.create_user(
            email=user_data.email,
            password=user_data.password,
            username=user_data.username,
            first_name=user_data.first_name,
            last_name=user_data.last_name
        )
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user"
            )
        
        await log_api_access(request, Response(status_code=201), current_user)
        
        return UserResponse(
            id=user_id,
            email=user_data.email,
            username=user_data.username,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            is_active=True,
            is_verified=False,
            created_at=datetime.utcnow(),
            last_login=None,
            mfa_enabled=False
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"User creation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User creation failed"
        )


# Credential management endpoints
@app.post("/credentials", response_model=Dict[str, str], tags=["Credentials"])
@limiter.limit("30/minute")
async def create_credential(
    request: Request,
    credential_data: CredentialCreateRequest,
    master_password: str = Field(..., description="Master password for encryption"),
    current_user: Dict[str, Any] = Depends(require_permission(Permission.CREATE_CREDENTIAL))
):
    """Create a new credential"""
    try:
        credential_id = await vault_core.store_credential(
            credential_data=credential_data.credential_data,
            master_password=master_password,
            organization_id=credential_data.organization_id,
            owner_id=current_user['user_id'],
            created_by=current_user['user_id'],
            environment_id=credential_data.environment_id,
            project_id=credential_data.project_id,
            service_id=credential_data.service_id
        )
        
        if not credential_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create credential"
            )
        
        # Process through hAIveMind analytics
        if haivemind_integration:
            event = {
                'event_type': 'credential_create',
                'user_id': current_user['user_id'],
                'credential_id': credential_id,
                'action': 'create_credential',
                'result': 'success',
                'timestamp': datetime.utcnow(),
                'ip_address': request.client.host,
                'credential_type': credential_data.credential_type.value,
                'risk_level': credential_data.risk_level.value
            }
            await haivemind_integration.process_vault_event(event)
        
        await log_api_access(request, Response(status_code=201), current_user)
        
        return {"credential_id": credential_id, "message": "Credential created successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Credential creation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Credential creation failed"
        )


@app.get("/credentials/{credential_id}", response_model=CredentialDataResponse, tags=["Credentials"])
@limiter.limit("100/minute")
async def get_credential(
    request: Request,
    credential_id: str,
    master_password: str = Field(..., description="Master password for decryption"),
    current_user: Dict[str, Any] = Depends(require_permission(Permission.READ_CREDENTIAL))
):
    """Retrieve and decrypt a credential"""
    try:
        credential_data = await vault_core.retrieve_credential(
            credential_id=credential_id,
            master_password=master_password,
            user_id=current_user['user_id'],
            ip_address=request.client.host
        )
        
        if not credential_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credential not found or access denied"
            )
        
        # Process through hAIveMind analytics
        if haivemind_integration:
            event = {
                'event_type': 'credential_access',
                'user_id': current_user['user_id'],
                'credential_id': credential_id,
                'action': 'retrieve_credential',
                'result': 'success',
                'timestamp': datetime.utcnow(),
                'ip_address': request.client.host
            }
            await haivemind_integration.process_vault_event(event)
        
        await log_api_access(request, Response(status_code=200), current_user)
        
        return CredentialDataResponse(
            credential_data=credential_data,
            metadata={
                'accessed_at': datetime.utcnow().isoformat(),
                'accessed_by': current_user['user_id']
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Credential retrieval error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Credential retrieval failed"
        )


@app.get("/credentials", response_model=List[CredentialResponse], tags=["Credentials"])
@limiter.limit("60/minute")
async def list_credentials(
    request: Request,
    organization_id: str,
    environment_id: Optional[str] = None,
    project_id: Optional[str] = None,
    service_id: Optional[str] = None,
    limit: int = Field(100, ge=1, le=1000),
    offset: int = Field(0, ge=0),
    current_user: Dict[str, Any] = Depends(require_permission(Permission.READ_CREDENTIAL))
):
    """List credentials with filtering"""
    try:
        credentials = await vault_core.list_credentials(
            organization_id=organization_id,
            user_id=current_user['user_id'],
            environment_id=environment_id,
            project_id=project_id,
            service_id=service_id,
            limit=limit,
            offset=offset
        )
        
        await log_api_access(request, Response(status_code=200), current_user)
        
        # Convert to response models
        response_credentials = []
        for cred in credentials:
            response_credentials.append(CredentialResponse(
                id=cred['id'],
                name=cred['name'],
                description=cred['description'],
                credential_type=CredentialType(cred['credential_type']),
                organization_id=organization_id,
                environment_id=environment_id,
                project_id=project_id,
                service_id=service_id,
                owner_id=current_user['user_id'],
                created_at=cred['created_at'],
                updated_at=cred['updated_at'],
                last_accessed=cred['last_accessed'],
                expires_at=cred['expires_at'],
                risk_level=RiskLevel(cred['risk_level']),
                tags=cred.get('tags', []),
                compliance_labels=cred.get('compliance_labels', []),
                access_count=cred.get('access_count', 0)
            ))
        
        return response_credentials
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Credential listing error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Credential listing failed"
        )


@app.delete("/credentials/{credential_id}", tags=["Credentials"])
@limiter.limit("20/minute")
async def delete_credential(
    request: Request,
    credential_id: str,
    hard_delete: bool = Field(False, description="Perform hard delete (permanent)"),
    current_user: Dict[str, Any] = Depends(require_permission(Permission.DELETE_CREDENTIAL))
):
    """Delete a credential"""
    try:
        success = await vault_core.delete_credential(
            credential_id=credential_id,
            user_id=current_user['user_id'],
            hard_delete=hard_delete
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credential not found or deletion failed"
            )
        
        # Process through hAIveMind analytics
        if haivemind_integration:
            event = {
                'event_type': 'credential_delete',
                'user_id': current_user['user_id'],
                'credential_id': credential_id,
                'action': 'delete_credential',
                'result': 'success',
                'timestamp': datetime.utcnow(),
                'ip_address': request.client.host,
                'hard_delete': hard_delete
            }
            await haivemind_integration.process_vault_event(event)
        
        await log_api_access(request, Response(status_code=200), current_user)
        
        return {
            "message": f"Credential {'permanently deleted' if hard_delete else 'deleted'} successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Credential deletion error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Credential deletion failed"
        )


# Compliance and audit endpoints
@app.post("/compliance/reports", tags=["Compliance"])
@limiter.limit("5/minute")
async def generate_compliance_report(
    request: Request,
    report_request: ComplianceReportRequest,
    current_user: Dict[str, Any] = Depends(require_permission(Permission.VIEW_AUDIT_LOGS))
):
    """Generate compliance report"""
    try:
        if not enterprise_integration:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Enterprise integration not available"
            )
        
        report = await enterprise_integration.compliance_engine.generate_compliance_report(
            standard=report_request.standard,
            start_date=report_request.start_date,
            end_date=report_request.end_date
        )
        
        if 'error' in report:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Report generation failed: {report['error']}"
            )
        
        await log_api_access(request, Response(status_code=200), current_user)
        
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Compliance report error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Compliance report generation failed"
        )


@app.post("/audit/export", tags=["Audit"])
@limiter.limit("3/minute")
async def export_audit_trail(
    request: Request,
    export_request: AuditExportRequest,
    current_user: Dict[str, Any] = Depends(require_permission(Permission.VIEW_AUDIT_LOGS))
):
    """Export audit trail"""
    try:
        if not enterprise_integration:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Enterprise integration not available"
            )
        
        audit_data = await enterprise_integration.compliance_engine.export_audit_trail(
            start_date=export_request.start_date,
            end_date=export_request.end_date,
            format=export_request.format
        )
        
        if not audit_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No audit data found for the specified period"
            )
        
        await log_api_access(request, Response(status_code=200), current_user)
        
        # Return as streaming response
        media_type = "text/csv" if export_request.format == "csv" else "application/json"
        filename = f"audit_trail_{export_request.start_date.date()}_{export_request.end_date.date()}.{export_request.format}"
        
        return StreamingResponse(
            iter([audit_data]),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Audit export error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Audit export failed"
        )


# System administration endpoints
@app.get("/system/status", tags=["System"])
@limiter.limit("30/minute")
async def system_status(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_permission(Permission.SYSTEM_ADMIN))
):
    """Get system status and metrics"""
    try:
        status_info = {
            "timestamp": datetime.utcnow().isoformat(),
            "vault_core": {
                "status": "healthy" if vault_core else "unavailable",
                "database_connected": bool(vault_core and vault_core.database.pool)
            },
            "authentication": {
                "status": "healthy" if auth_manager else "unavailable"
            },
            "enterprise_integration": {
                "status": "healthy" if enterprise_integration else "unavailable"
            },
            "haivemind_integration": {
                "status": "healthy" if haivemind_integration else "unavailable"
            },
            "redis": {
                "status": "healthy" if redis_client else "unavailable"
            }
        }
        
        await log_api_access(request, Response(status_code=200), current_user)
        
        return status_info
        
    except Exception as e:
        logging.error(f"System status error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="System status check failed"
        )


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logging.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    logging.basicConfig(level=logging.INFO)
    
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
        ssl_keyfile=None,  # Add SSL certificate paths for production
        ssl_certfile=None,
        log_level="info"
    )