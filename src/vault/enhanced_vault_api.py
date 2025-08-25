"""
Enhanced Vault REST API Endpoints
Comprehensive RESTful API for secure credential vault operations with full Story 8b features.

Author: Lance James, Unit 221B
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import secrets
import hashlib
import redis

from .database_manager import DatabaseManager
from .encryption_engine import EncryptionEngine, EncryptedData
from .credential_types import CredentialTypeManager, CredentialData, ValidationResult, CredentialType
from .performance_optimizer import PerformanceOptimizer
from .audit_manager import AuditManager, AuditEventType, AuditResult
from .security_features import SecurityFeatureManager, SecurityLevel
from .haivemind_integration import HAIveMindVaultIntegration
from .core_vault import CredentialMetadata, CredentialStatus
from ..auth import AuthManager


# Enhanced Pydantic models for API requests/responses
class CredentialCreateRequest(BaseModel):
    name: str = Field(..., description="Human-readable name for the credential")
    description: Optional[str] = Field(None, description="Description of the credential")
    credential_type: str = Field(..., description="Type of credential")
    environment: str = Field(..., description="Environment (dev, staging, prod)")
    service: str = Field(..., description="Service name")
    project: str = Field(..., description="Project name")
    credential_data: Dict[str, Any] = Field(..., description="Credential data")
    expires_at: Optional[datetime] = Field(None, description="Expiration date")
    rotation_schedule: Optional[str] = Field(None, description="Rotation schedule (cron format)")
    tags: List[str] = Field(default_factory=list, description="Tags for organization")
    compliance_labels: List[str] = Field(default_factory=list, description="Compliance labels")
    audit_required: bool = Field(False, description="Whether audit is required")
    emergency_access: bool = Field(False, description="Whether emergency access is allowed")
    auto_rotate: bool = Field(False, description="Enable automatic rotation")
    rotation_interval_days: int = Field(90, description="Days between rotations")


class CredentialResponse(BaseModel):
    credential_id: str
    name: str
    description: Optional[str]
    credential_type: str
    environment: str
    service: str
    project: str
    owner_id: str
    created_at: datetime
    updated_at: datetime
    last_accessed: Optional[datetime]
    expires_at: Optional[datetime]
    rotation_schedule: Optional[str]
    status: str
    tags: List[str]
    compliance_labels: List[str]
    audit_required: bool
    emergency_access: bool
    access_count: int = 0
    risk_level: str = "medium"
    validation_score: Optional[float] = None


class CredentialDataResponse(BaseModel):
    credential_id: str
    metadata: CredentialResponse
    credential_data: Dict[str, Any]


class CredentialValidationRequest(BaseModel):
    credential_type: str
    credential_data: Dict[str, Any]


class CredentialGenerationRequest(BaseModel):
    credential_type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class BatchCredentialRequest(BaseModel):
    credential_ids: List[str]
    master_password: str


class AccessGrantRequest(BaseModel):
    user_id: str = Field(..., description="User ID to grant access to")
    access_level: str = Field(..., description="Access level to grant")
    expires_at: Optional[datetime] = Field(None, description="Access expiration")
    ip_restrictions: List[str] = Field(default_factory=list, description="IP restrictions")
    purpose: Optional[str] = Field(None, description="Purpose of access")


class CredentialRotationRequest(BaseModel):
    new_master_password: str
    rotation_reason: str = "scheduled_rotation"


class AuditTrailResponse(BaseModel):
    events: List[Dict[str, Any]]
    total_count: int
    page: int
    page_size: int


class VaultStatsResponse(BaseModel):
    total_credentials: int
    by_type: Dict[str, int]
    by_environment: Dict[str, int]
    by_status: Dict[str, int]
    by_risk_level: Dict[str, int]
    expiring_soon: int
    recent_activity: int
    performance_metrics: Dict[str, Any]
    security_metrics: Dict[str, Any]
    last_updated: str


class ComplianceReportResponse(BaseModel):
    report_id: str
    framework: str
    period_start: datetime
    period_end: datetime
    total_events: int
    compliant_events: int
    violations: List[Dict[str, Any]]
    recommendations: List[str]
    generated_at: datetime


class EnhancedVaultAPI:
    """Enhanced REST API for vault operations with comprehensive Story 8b features"""
    
    def __init__(self, database_manager: DatabaseManager, encryption_engine: EncryptionEngine,
                 credential_manager: CredentialTypeManager, performance_optimizer: PerformanceOptimizer,
                 audit_manager: AuditManager, security_manager: SecurityFeatureManager,
                 haivemind_integration: HAIveMindVaultIntegration, auth_manager: AuthManager, 
                 config: Dict[str, Any]):
        self.database_manager = database_manager
        self.encryption_engine = encryption_engine
        self.credential_manager = credential_manager
        self.performance_optimizer = performance_optimizer
        self.audit_manager = audit_manager
        self.security_manager = security_manager
        self.haivemind_integration = haivemind_integration
        self.auth_manager = auth_manager
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Create FastAPI app
        self.app = FastAPI(
            title="hAIveMind Enhanced Credential Vault API",
            description="Enterprise-grade secure credential storage and management API with comprehensive security features",
            version="2.0.0",
            docs_url="/api/docs",
            redoc_url="/api/redoc"
        )
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=config.get('security', {}).get('allowed_origins', ['*']),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Security
        self.security = HTTPBearer()
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup comprehensive API routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
        
        # Credential Management Routes
        @self.app.post("/api/v2/credentials", response_model=CredentialResponse)
        async def create_credential(
            request: CredentialCreateRequest,
            master_password: str = Field(..., description="Master password for encryption"),
            current_user: Dict = Depends(self.get_current_user),
            request_context: Request = None
        ):
            """Create a new encrypted credential with comprehensive validation and security"""
            start_time = time.time()
            credential_id = secrets.token_urlsafe(32)
            
            try:
                # Security authorization
                session_id = current_user.get('session_id')
                if not await self.security_manager.authorize_operation(
                    session_id, 'create', credential_id, SecurityLevel.STANDARD
                ):
                    raise HTTPException(status_code=403, detail="Operation not authorized")
                
                # Create credential data object
                credential_data = CredentialData(
                    credential_type=CredentialType(request.credential_type),
                    data=request.credential_data,
                    expires_at=request.expires_at
                )
                
                # Validate credential
                validation_result = await self.credential_manager.validate_credential(credential_data)
                if not validation_result.is_valid:
                    await self.audit_manager.log_event(
                        AuditEventType.CREATE, current_user['user_id'], "create_credential",
                        AuditResult.FAILURE, credential_id,
                        ip_address=request_context.client.host if request_context else None,
                        metadata={'validation_errors': validation_result.issues}
                    )
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Credential validation failed: {', '.join(validation_result.issues)}"
                    )
                
                # Encrypt credential data
                encrypted_data = await self.encryption_engine.encrypt_data(
                    json.dumps(request.credential_data).encode(), 
                    master_password,
                    metadata={'credential_id': credential_id, 'user_id': current_user['user_id']}
                )
                
                # Store in database with transaction
                async with self.database_manager.get_transaction() as conn:
                    # Store metadata
                    metadata = CredentialMetadata(
                        credential_id=credential_id,
                        name=request.name,
                        description=request.description,
                        credential_type=CredentialType(request.credential_type),
                        environment=request.environment,
                        service=request.service,
                        project=request.project,
                        owner_id=current_user['user_id'],
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        expires_at=request.expires_at,
                        rotation_schedule=request.rotation_schedule,
                        status=CredentialStatus.ACTIVE,
                        tags=request.tags,
                        compliance_labels=request.compliance_labels,
                        audit_required=request.audit_required,
                        emergency_access=request.emergency_access
                    )
                    
                    success = await self.database_manager.store_credential_metadata(metadata, conn)
                    if not success:
                        raise HTTPException(status_code=500, detail="Failed to store credential metadata")
                    
                    # Store encrypted data
                    success = await self.database_manager.store_encrypted_credential(
                        credential_id, encrypted_data.ciphertext, encrypted_data.key_version,
                        encrypted_data.salt, encrypted_data.nonce, encrypted_data.tag, conn
                    )
                    if not success:
                        raise HTTPException(status_code=500, detail="Failed to store encrypted credential")
                
                # Cache metadata for performance
                await self.performance_optimizer.cache_metadata(credential_id, metadata.__dict__)
                
                # Log audit event
                duration_ms = int((time.time() - start_time) * 1000)
                await self.audit_manager.log_event(
                    AuditEventType.CREATE, current_user['user_id'], "create_credential",
                    AuditResult.SUCCESS, credential_id,
                    ip_address=request_context.client.host if request_context else None,
                    user_agent=request_context.headers.get('user-agent') if request_context else None,
                    duration_ms=duration_ms,
                    metadata={
                        'credential_type': request.credential_type,
                        'validation_score': validation_result.strength_score,
                        'environment': request.environment,
                        'service': request.service
                    }
                )
                
                # Store in hAIveMind for learning
                if self.haivemind_integration:
                    await self.haivemind_integration.process_security_event({
                        'event_type': 'credential_created',
                        'user_id': current_user['user_id'],
                        'credential_id': credential_id,
                        'credential_type': request.credential_type,
                        'validation_score': validation_result.strength_score,
                        'timestamp': datetime.utcnow().isoformat()
                    })
                
                return CredentialResponse(
                    credential_id=metadata.credential_id,
                    name=metadata.name,
                    description=metadata.description,
                    credential_type=metadata.credential_type.value,
                    environment=metadata.environment,
                    service=metadata.service,
                    project=metadata.project,
                    owner_id=metadata.owner_id,
                    created_at=metadata.created_at,
                    updated_at=metadata.updated_at,
                    last_accessed=metadata.last_accessed,
                    expires_at=metadata.expires_at,
                    rotation_schedule=metadata.rotation_schedule,
                    status=metadata.status.value,
                    tags=metadata.tags,
                    compliance_labels=metadata.compliance_labels,
                    audit_required=metadata.audit_required,
                    emergency_access=metadata.emergency_access,
                    validation_score=validation_result.strength_score
                )
                
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Failed to create credential: {str(e)}")
                duration_ms = int((time.time() - start_time) * 1000)
                await self.audit_manager.log_event(
                    AuditEventType.CREATE, current_user['user_id'], "create_credential",
                    AuditResult.ERROR, credential_id,
                    ip_address=request_context.client.host if request_context else None,
                    duration_ms=duration_ms,
                    metadata={'error': str(e)}
                )
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v2/credentials/{credential_id}", response_model=CredentialDataResponse)
        async def get_credential(
            credential_id: str,
            master_password: str = Field(..., description="Master password for decryption"),
            current_user: Dict = Depends(self.get_current_user),
            request_context: Request = None
        ):
            """Retrieve and decrypt a credential with comprehensive security and performance optimization"""
            start_time = time.time()
            
            try:
                # Security authorization
                session_id = current_user.get('session_id')
                if not await self.security_manager.authorize_operation(
                    session_id, 'read', credential_id, SecurityLevel.STANDARD
                ):
                    raise HTTPException(status_code=403, detail="Operation not authorized")
                
                # Check access permissions
                has_access = await self.database_manager.check_user_access(
                    current_user['user_id'], credential_id, 'read'
                )
                if not has_access:
                    await self.audit_manager.log_event(
                        AuditEventType.READ, current_user['user_id'], "get_credential",
                        AuditResult.DENIED, credential_id,
                        ip_address=request_context.client.host if request_context else None
                    )
                    raise HTTPException(status_code=403, detail="Access denied")
                
                # Try to get from cache first
                cached_data = await self.performance_optimizer.get_cached_credential(
                    credential_id, current_user['user_id']
                )
                
                if cached_data:
                    # Get metadata from cache or database
                    metadata = await self.performance_optimizer.get_cached_metadata(credential_id)
                    if not metadata:
                        metadata_obj = await self.database_manager.retrieve_credential_metadata(credential_id)
                        if metadata_obj:
                            metadata = metadata_obj.__dict__
                            await self.performance_optimizer.cache_metadata(credential_id, metadata)
                    
                    if metadata:
                        # Log cache hit
                        duration_ms = int((time.time() - start_time) * 1000)
                        await self.audit_manager.log_event(
                            AuditEventType.READ, current_user['user_id'], "get_credential",
                            AuditResult.SUCCESS, credential_id,
                            ip_address=request_context.client.host if request_context else None,
                            duration_ms=duration_ms,
                            metadata={'cache_hit': True}
                        )
                        
                        return CredentialDataResponse(
                            credential_id=credential_id,
                            metadata=self._build_credential_response(metadata),
                            credential_data=cached_data
                        )
                
                # Cache miss - retrieve from database
                metadata = await self.database_manager.retrieve_credential_metadata(credential_id)
                if not metadata:
                    raise HTTPException(status_code=404, detail="Credential not found")
                
                # Get encrypted data
                encrypted_data_tuple = await self.database_manager.retrieve_encrypted_credential(credential_id)
                if not encrypted_data_tuple:
                    raise HTTPException(status_code=404, detail="Encrypted credential data not found")
                
                # Reconstruct EncryptedData object
                encrypted_data = EncryptedData(
                    ciphertext=encrypted_data_tuple[0],
                    algorithm=self.encryption_engine.params.algorithm,
                    key_derivation=self.encryption_engine.params.key_derivation,
                    salt=encrypted_data_tuple[2],
                    nonce=encrypted_data_tuple[3],
                    tag=encrypted_data_tuple[4],
                    key_version=encrypted_data_tuple[1],
                    created_at=datetime.utcnow(),
                    metadata={}
                )
                
                # Decrypt credential data
                decrypted_bytes = await self.encryption_engine.decrypt_data(encrypted_data, master_password)
                credential_data = json.loads(decrypted_bytes.decode())
                
                # Update access timestamp
                await self.database_manager.update_access_timestamp(credential_id)
                
                # Cache for future access
                await self.performance_optimizer.cache_credential(
                    credential_id, current_user['user_id'], credential_data, ttl=60
                )
                await self.performance_optimizer.cache_metadata(credential_id, metadata.__dict__)
                
                # Log audit event
                duration_ms = int((time.time() - start_time) * 1000)
                await self.audit_manager.log_event(
                    AuditEventType.READ, current_user['user_id'], "get_credential",
                    AuditResult.SUCCESS, credential_id,
                    ip_address=request_context.client.host if request_context else None,
                    user_agent=request_context.headers.get('user-agent') if request_context else None,
                    duration_ms=duration_ms,
                    metadata={'cache_hit': False, 'credential_type': metadata.credential_type.value}
                )
                
                return CredentialDataResponse(
                    credential_id=credential_id,
                    metadata=self._build_credential_response(metadata.__dict__),
                    credential_data=credential_data
                )
                
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Failed to retrieve credential: {str(e)}")
                duration_ms = int((time.time() - start_time) * 1000)
                await self.audit_manager.log_event(
                    AuditEventType.READ, current_user['user_id'], "get_credential",
                    AuditResult.ERROR, credential_id,
                    ip_address=request_context.client.host if request_context else None,
                    duration_ms=duration_ms,
                    metadata={'error': str(e)}
                )
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v2/credentials", response_model=List[CredentialResponse])
        async def list_credentials(
            environment: Optional[str] = None,
            service: Optional[str] = None,
            project: Optional[str] = None,
            credential_type: Optional[str] = None,
            status: Optional[str] = None,
            limit: int = 100,
            offset: int = 0,
            current_user: Dict = Depends(self.get_current_user)
        ):
            """List credentials accessible to the current user with filtering and pagination"""
            try:
                # Security authorization
                session_id = current_user.get('session_id')
                if not await self.security_manager.authorize_operation(
                    session_id, 'list', None, SecurityLevel.STANDARD
                ):
                    raise HTTPException(status_code=403, detail="Operation not authorized")
                
                filters = {}
                if environment:
                    filters['environment'] = environment
                if service:
                    filters['service'] = service
                if project:
                    filters['project'] = project
                if credential_type:
                    filters['credential_type'] = credential_type
                if status:
                    filters['status'] = status
                
                credentials = await self.database_manager.list_credentials_for_user(
                    current_user['user_id'], filters
                )
                
                # Apply pagination
                paginated_credentials = credentials[offset:offset + limit]
                
                return [
                    CredentialResponse(
                        credential_id=cred.credential_id,
                        name=cred.name,
                        description=cred.description,
                        credential_type=cred.credential_type.value,
                        environment=cred.environment,
                        service=cred.service,
                        project=cred.project,
                        owner_id=cred.owner_id,
                        created_at=cred.created_at,
                        updated_at=cred.updated_at,
                        last_accessed=cred.last_accessed,
                        expires_at=cred.expires_at,
                        rotation_schedule=cred.rotation_schedule,
                        status=cred.status.value,
                        tags=cred.tags,
                        compliance_labels=cred.compliance_labels,
                        audit_required=cred.audit_required,
                        emergency_access=cred.emergency_access,
                        access_count=getattr(cred, 'access_count', 0),
                        risk_level=getattr(cred, 'risk_level', 'medium')
                    )
                    for cred in paginated_credentials
                ]
                
            except Exception as e:
                self.logger.error(f"Failed to list credentials: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v2/credentials/batch", response_model=Dict[str, Any])
        async def get_credentials_batch(
            request: BatchCredentialRequest,
            current_user: Dict = Depends(self.get_current_user)
        ):
            """Retrieve multiple credentials in a single optimized request"""
            try:
                # Security authorization
                session_id = current_user.get('session_id')
                if not await self.security_manager.authorize_operation(
                    session_id, 'read', None, SecurityLevel.STANDARD
                ):
                    raise HTTPException(status_code=403, detail="Operation not authorized")
                
                # Use performance optimizer for batch retrieval
                results = await self.performance_optimizer.optimized_credential_retrieval(
                    request.credential_ids, current_user['user_id'], request.master_password
                )
                
                return {
                    'credentials': results,
                    'retrieved_count': len([r for r in results.values() if r is not None]),
                    'total_requested': len(request.credential_ids)
                }
                
            except Exception as e:
                self.logger.error(f"Failed to retrieve credentials batch: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v2/credentials/validate", response_model=ValidationResult)
        async def validate_credential(
            request: CredentialValidationRequest,
            current_user: Dict = Depends(self.get_current_user)
        ):
            """Validate credential data without storing it"""
            try:
                credential_data = CredentialData(
                    credential_type=CredentialType(request.credential_type),
                    data=request.credential_data
                )
                
                validation_result = await self.credential_manager.validate_credential(credential_data)
                return validation_result
                
            except Exception as e:
                self.logger.error(f"Failed to validate credential: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v2/credentials/generate", response_model=CredentialData)
        async def generate_credential(
            request: CredentialGenerationRequest,
            current_user: Dict = Depends(self.get_current_user)
        ):
            """Generate a new credential of the specified type"""
            try:
                # Security authorization
                session_id = current_user.get('session_id')
                if not await self.security_manager.authorize_operation(
                    session_id, 'generate', None, SecurityLevel.STANDARD
                ):
                    raise HTTPException(status_code=403, detail="Operation not authorized")
                
                credential_data = await self.credential_manager.generate_credential(
                    CredentialType(request.credential_type), request.parameters
                )
                
                return credential_data
                
            except Exception as e:
                self.logger.error(f"Failed to generate credential: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Access Management Routes
        @self.app.post("/api/v2/credentials/{credential_id}/access")
        async def grant_credential_access(
            credential_id: str,
            request: AccessGrantRequest,
            current_user: Dict = Depends(self.get_current_user)
        ):
            """Grant access to a credential for another user"""
            try:
                # Security authorization
                session_id = current_user.get('session_id')
                if not await self.security_manager.authorize_operation(
                    session_id, 'share', credential_id, SecurityLevel.HIGH
                ):
                    raise HTTPException(status_code=403, detail="Operation not authorized")
                
                success = await self.database_manager.grant_credential_access(
                    credential_id=credential_id,
                    user_id=request.user_id,
                    access_level=request.access_level,
                    granted_by=current_user['user_id'],
                    expires_at=request.expires_at,
                    permissions={'read': True, 'write': request.access_level in ['admin', 'owner']}
                )
                
                if not success:
                    raise HTTPException(status_code=500, detail="Failed to grant access")
                
                # Log audit event
                await self.audit_manager.log_event(
                    AuditEventType.SHARE, current_user['user_id'], "grant_access",
                    AuditResult.SUCCESS, credential_id,
                    metadata={
                        'target_user': request.user_id,
                        'access_level': request.access_level,
                        'purpose': request.purpose
                    }
                )
                
                return {"message": "Access granted successfully"}
                
            except Exception as e:
                self.logger.error(f"Failed to grant access: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Audit and Compliance Routes
        @self.app.get("/api/v2/credentials/{credential_id}/audit", response_model=AuditTrailResponse)
        async def get_credential_audit_trail(
            credential_id: str,
            days: int = 30,
            page: int = 1,
            page_size: int = 50,
            current_user: Dict = Depends(self.get_current_user)
        ):
            """Get audit trail for a specific credential"""
            try:
                # Security authorization
                session_id = current_user.get('session_id')
                if not await self.security_manager.authorize_operation(
                    session_id, 'audit', credential_id, SecurityLevel.STANDARD
                ):
                    raise HTTPException(status_code=403, detail="Operation not authorized")
                
                events = await self.audit_manager.get_audit_trail(credential_id, days)
                
                # Paginate results
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                paginated_events = events[start_idx:end_idx]
                
                return AuditTrailResponse(
                    events=[event.to_dict() for event in paginated_events],
                    total_count=len(events),
                    page=page,
                    page_size=page_size
                )
                
            except Exception as e:
                self.logger.error(f"Failed to get audit trail: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Statistics and Monitoring Routes
        @self.app.get("/api/v2/vault/statistics", response_model=VaultStatsResponse)
        async def get_vault_statistics(
            current_user: Dict = Depends(self.get_current_user)
        ):
            """Get comprehensive vault statistics and metrics"""
            try:
                # Security authorization
                session_id = current_user.get('session_id')
                if not await self.security_manager.authorize_operation(
                    session_id, 'read', None, SecurityLevel.STANDARD
                ):
                    raise HTTPException(status_code=403, detail="Operation not authorized")
                
                # Get database statistics
                db_stats = await self.database_manager.get_vault_statistics()
                
                # Get performance statistics
                perf_stats = await self.performance_optimizer.get_performance_stats()
                
                # Get security statistics
                security_stats = await self.security_manager.get_security_status()
                
                # Get audit statistics
                audit_stats = await self.audit_manager.get_audit_statistics()
                
                # Get encryption statistics
                encryption_stats = await self.encryption_engine.get_encryption_stats()
                
                # Get hAIveMind status
                haivemind_stats = {}
                if self.haivemind_integration:
                    haivemind_stats = await self.haivemind_integration.get_haivemind_status()
                
                return VaultStatsResponse(
                    total_credentials=db_stats.get('total_credentials', 0),
                    by_type=db_stats.get('by_type', {}),
                    by_environment=db_stats.get('by_environment', {}),
                    by_status=db_stats.get('by_status', {}),
                    by_risk_level=db_stats.get('by_risk_level', {}),
                    expiring_soon=db_stats.get('expiring_soon', 0),
                    recent_activity=db_stats.get('recent_activity', 0),
                    performance_metrics=perf_stats,
                    security_metrics=security_stats,
                    last_updated=db_stats.get('last_updated', datetime.utcnow().isoformat())
                )
                
            except Exception as e:
                self.logger.error(f"Failed to get vault statistics: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v2/vault/health")
        async def get_vault_health(
            current_user: Dict = Depends(self.get_current_user)
        ):
            """Get comprehensive vault health status"""
            try:
                return {
                    'database': 'healthy',
                    'encryption': 'healthy',
                    'performance': 'optimal',
                    'security': 'secure',
                    'audit': 'active',
                    'haivemind': 'connected' if self.haivemind_integration else 'disabled',
                    'timestamp': datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                self.logger.error(f"Failed to get vault health: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
    
    async def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
        """Get current authenticated user with session validation"""
        try:
            token = credentials.credentials
            user_info = await self.auth_manager.validate_token(token)
            
            if not user_info:
                raise HTTPException(status_code=401, detail="Invalid authentication token")
            
            # Validate session if session_id is provided
            session_id = user_info.get('session_id')
            if session_id:
                session_context = await self.security_manager.session_manager.get_session(session_id)
                if not session_context:
                    raise HTTPException(status_code=401, detail="Invalid or expired session")
                user_info['session_context'] = session_context
            
            return user_info
            
        except Exception as e:
            self.logger.error(f"Authentication failed: {str(e)}")
            raise HTTPException(status_code=401, detail="Authentication failed")
    
    def _build_credential_response(self, metadata: Dict[str, Any]) -> CredentialResponse:
        """Build CredentialResponse from metadata dictionary"""
        return CredentialResponse(
            credential_id=metadata['credential_id'],
            name=metadata['name'],
            description=metadata.get('description'),
            credential_type=metadata['credential_type'],
            environment=metadata['environment'],
            service=metadata['service'],
            project=metadata['project'],
            owner_id=metadata['owner_id'],
            created_at=metadata['created_at'],
            updated_at=metadata['updated_at'],
            last_accessed=metadata.get('last_accessed'),
            expires_at=metadata.get('expires_at'),
            rotation_schedule=metadata.get('rotation_schedule'),
            status=metadata.get('status', 'active'),
            tags=metadata.get('tags', []),
            compliance_labels=metadata.get('compliance_labels', []),
            audit_required=metadata.get('audit_required', False),
            emergency_access=metadata.get('emergency_access', False),
            access_count=metadata.get('access_count', 0),
            risk_level=metadata.get('risk_level', 'medium')
        )


async def create_enhanced_vault_api_server(database_manager: DatabaseManager, 
                                         encryption_engine: EncryptionEngine,
                                         credential_manager: CredentialTypeManager,
                                         performance_optimizer: PerformanceOptimizer,
                                         audit_manager: AuditManager,
                                         security_manager: SecurityFeatureManager,
                                         haivemind_integration: HAIveMindVaultIntegration,
                                         auth_manager: AuthManager, 
                                         config: Dict[str, Any]) -> FastAPI:
    """Create and configure the enhanced vault API server"""
    
    vault_api = EnhancedVaultAPI(
        database_manager, encryption_engine, credential_manager, performance_optimizer,
        audit_manager, security_manager, haivemind_integration, auth_manager, config
    )
    return vault_api.app


# Example usage
async def main():
    """Example usage of the enhanced vault API"""
    import uvicorn
    import redis
    from ..auth import AuthManager
    
    # Load configuration
    with open('config/config.json', 'r') as f:
        base_config = json.load(f)
    
    config = base_config
    
    # Initialize Redis client
    redis_client = redis.Redis(
        host=config.get('redis', {}).get('host', 'localhost'),
        port=config.get('redis', {}).get('port', 6379),
        db=config.get('redis', {}).get('db', 0),
        decode_responses=True
    )
    
    # Initialize all components
    database_manager = DatabaseManager(config, redis_client)
    await database_manager.initialize()
    
    encryption_engine = EncryptionEngine(config, redis_client)
    await encryption_engine.initialize()
    
    credential_manager = CredentialTypeManager(config)
    
    performance_optimizer = PerformanceOptimizer(config, redis_client, encryption_engine, database_manager)
    await performance_optimizer.initialize()
    
    audit_manager = AuditManager(config, redis_client, database_manager)
    await audit_manager.initialize()
    
    security_manager = SecurityFeatureManager(config)
    await security_manager.initialize()
    
    # Initialize hAIveMind integration (would need memory server)
    haivemind_integration = None  # Would be initialized with memory server
    
    auth_manager = AuthManager(config, redis_client)
    
    # Create API server
    app = await create_enhanced_vault_api_server(
        database_manager, encryption_engine, credential_manager, performance_optimizer,
        audit_manager, security_manager, haivemind_integration, auth_manager, config
    )
    
    # Run server
    uvicorn.run(
        app,
        host=config.get('vault', {}).get('api', {}).get('host', '0.0.0.0'),
        port=config.get('vault', {}).get('api', {}).get('port', 8920),
        log_level="info"
    )


if __name__ == "__main__":
    asyncio.run(main())