"""
Vault REST API Endpoints
RESTful API for secure credential vault operations.

Author: Lance James, Unit 221B
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import secrets
import hashlib
import redis

from .core_vault import CoreCredentialVault, CredentialMetadata, CredentialType, AccessLevel, CredentialStatus
from .enterprise_vault_orchestrator import EnterpriseVaultOrchestrator
from ..auth import AuthManager


# Pydantic models for API requests/responses
class CredentialCreateRequest(BaseModel):
    name: str = Field(..., description="Human-readable name for the credential")
    description: Optional[str] = Field(None, description="Description of the credential")
    credential_type: str = Field(..., description="Type of credential")
    environment: str = Field(..., description="Environment (dev, staging, prod)")
    service: str = Field(..., description="Service name")
    project: str = Field(..., description="Project name")
    credential_data: Dict[str, Any] = Field(..., description="Encrypted credential data")
    expires_at: Optional[datetime] = Field(None, description="Expiration date")
    rotation_schedule: Optional[str] = Field(None, description="Rotation schedule (cron format)")
    tags: List[str] = Field(default_factory=list, description="Tags for organization")
    compliance_labels: List[str] = Field(default_factory=list, description="Compliance labels")
    audit_required: bool = Field(False, description="Whether audit is required")
    emergency_access: bool = Field(False, description="Whether emergency access is allowed")


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


class CredentialDataResponse(BaseModel):
    credential_id: str
    metadata: CredentialResponse
    credential_data: Dict[str, Any]


class AccessGrantRequest(BaseModel):
    user_id: str = Field(..., description="User ID to grant access to")
    access_level: str = Field(..., description="Access level to grant")
    expires_at: Optional[datetime] = Field(None, description="Access expiration")
    ip_restrictions: List[str] = Field(default_factory=list, description="IP restrictions")
    purpose: Optional[str] = Field(None, description="Purpose of access")


class VaultStatsResponse(BaseModel):
    total_credentials: int
    by_type: Dict[str, int]
    by_environment: Dict[str, int]
    by_status: Dict[str, int]
    expiring_soon: int
    recent_activity: int
    last_updated: str


class VaultAPI:
    """REST API for vault operations"""
    
    def __init__(self, vault_orchestrator: EnterpriseVaultOrchestrator, 
                 auth_manager: AuthManager, config: Dict[str, Any]):
        self.vault = vault_orchestrator
        self.core_vault = vault_orchestrator.security_framework  # Access core vault through orchestrator
        self.auth_manager = auth_manager
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Create FastAPI app
        self.app = FastAPI(
            title="hAIveMind Credential Vault API",
            description="Secure credential storage and management API",
            version="1.0.0"
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
        """Setup API routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
        
        @self.app.post("/api/v1/credentials", response_model=CredentialResponse)
        async def create_credential(
            request: CredentialCreateRequest,
            master_password: str = Field(..., description="Master password for encryption"),
            current_user: Dict = Depends(self.get_current_user)
        ):
            """Create a new encrypted credential"""
            try:
                # Generate credential ID
                credential_id = secrets.token_urlsafe(32)
                
                # Create metadata
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
                    last_accessed=None,
                    expires_at=request.expires_at,
                    rotation_schedule=request.rotation_schedule,
                    status=CredentialStatus.ACTIVE,
                    tags=request.tags,
                    compliance_labels=request.compliance_labels,
                    audit_required=request.audit_required,
                    emergency_access=request.emergency_access
                )
                
                # Store credential
                success = await self.core_vault.store_credential(
                    metadata, request.credential_data, master_password, current_user['user_id']
                )
                
                if not success:
                    raise HTTPException(status_code=500, detail="Failed to store credential")
                
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
                    emergency_access=metadata.emergency_access
                )
                
            except Exception as e:
                self.logger.error(f"Failed to create credential: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/credentials/{credential_id}", response_model=CredentialDataResponse)
        async def get_credential(
            credential_id: str,
            master_password: str = Field(..., description="Master password for decryption"),
            current_user: Dict = Depends(self.get_current_user)
        ):
            """Retrieve and decrypt a credential"""
            try:
                result = await self.core_vault.retrieve_credential(
                    credential_id, master_password, current_user['user_id']
                )
                
                if not result:
                    raise HTTPException(status_code=404, detail="Credential not found or access denied")
                
                metadata, credential_data = result
                
                return CredentialDataResponse(
                    credential_id=credential_id,
                    metadata=CredentialResponse(
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
                        emergency_access=metadata.emergency_access
                    ),
                    credential_data=credential_data
                )
                
            except Exception as e:
                self.logger.error(f"Failed to retrieve credential: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/credentials", response_model=List[CredentialResponse])
        async def list_credentials(
            environment: Optional[str] = None,
            service: Optional[str] = None,
            project: Optional[str] = None,
            credential_type: Optional[str] = None,
            status: Optional[str] = None,
            current_user: Dict = Depends(self.get_current_user)
        ):
            """List credentials accessible to the current user"""
            try:
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
                
                credentials = await self.core_vault.list_credentials(current_user['user_id'], filters)
                
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
                        emergency_access=cred.emergency_access
                    )
                    for cred in credentials
                ]
                
            except Exception as e:
                self.logger.error(f"Failed to list credentials: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/credentials/{credential_id}/access")
        async def grant_credential_access(
            credential_id: str,
            request: AccessGrantRequest,
            current_user: Dict = Depends(self.get_current_user)
        ):
            """Grant access to a credential for another user"""
            try:
                success = await self.core_vault.grant_access(
                    credential_id=credential_id,
                    user_id=request.user_id,
                    access_level=AccessLevel(request.access_level),
                    granted_by=current_user['user_id'],
                    expires_at=request.expires_at,
                    ip_restrictions=request.ip_restrictions,
                    purpose=request.purpose
                )
                
                if not success:
                    raise HTTPException(status_code=500, detail="Failed to grant access")
                
                return {"message": "Access granted successfully"}
                
            except Exception as e:
                self.logger.error(f"Failed to grant access: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/vault/statistics", response_model=VaultStatsResponse)
        async def get_vault_statistics(
            current_user: Dict = Depends(self.get_current_user)
        ):
            """Get vault statistics and metrics"""
            try:
                stats = await self.core_vault.get_vault_statistics()
                
                return VaultStatsResponse(
                    total_credentials=stats.get('total_credentials', 0),
                    by_type=stats.get('by_type', {}),
                    by_environment=stats.get('by_environment', {}),
                    by_status=stats.get('by_status', {}),
                    expiring_soon=stats.get('expiring_soon', 0),
                    recent_activity=stats.get('recent_activity', 0),
                    last_updated=stats.get('last_updated', datetime.utcnow().isoformat())
                )
                
            except Exception as e:
                self.logger.error(f"Failed to get vault statistics: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/vault/status")
        async def get_vault_status(
            current_user: Dict = Depends(self.get_current_user)
        ):
            """Get comprehensive vault status"""
            try:
                status = await self.vault.get_vault_status()
                return {"vault_status": status}
                
            except Exception as e:
                self.logger.error(f"Failed to get vault status: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/vault/emergency/revoke")
        async def emergency_credential_revocation(
            credential_ids: List[str],
            reason: str,
            current_user: Dict = Depends(self.get_current_user)
        ):
            """Emergency revocation of credentials"""
            try:
                # Check if user has emergency access
                if not current_user.get('emergency_access', False):
                    raise HTTPException(status_code=403, detail="Emergency access required")
                
                # Use vault tools for emergency revocation
                from ..vault_mcp_tools import VaultMCPTools
                vault_tools = VaultMCPTools(self.vault, self.vault.memory_server)
                
                result = await vault_tools.emergency_credential_revocation(
                    credential_ids, reason, current_user['user_id']
                )
                
                return result
                
            except Exception as e:
                self.logger.error(f"Emergency revocation failed: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
    
    async def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
        """Get current authenticated user"""
        try:
            token = credentials.credentials
            user_info = await self.auth_manager.validate_token(token)
            
            if not user_info:
                raise HTTPException(status_code=401, detail="Invalid authentication token")
            
            return user_info
            
        except Exception as e:
            self.logger.error(f"Authentication failed: {str(e)}")
            raise HTTPException(status_code=401, detail="Authentication failed")


async def create_vault_api_server(vault_orchestrator: EnterpriseVaultOrchestrator,
                                auth_manager: AuthManager, config: Dict[str, Any]) -> FastAPI:
    """Create and configure the vault API server"""
    
    vault_api = VaultAPI(vault_orchestrator, auth_manager, config)
    return vault_api.app


# Example usage
async def main():
    """Example usage of the vault API"""
    import uvicorn
    from ..auth import AuthManager
    
    # Load configuration
    with open('config/config.json', 'r') as f:
        base_config = json.load(f)
    
    with open('config/vault_config.json', 'r') as f:
        vault_config = json.load(f)
    
    config = {**base_config, **vault_config}
    
    # Initialize components (would be done in main application)
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    auth_manager = AuthManager(config, redis_client)
    
    # Initialize vault orchestrator (placeholder)
    vault_orchestrator = None  # Would be initialized with proper components
    
    if vault_orchestrator:
        # Create API server
        app = await create_vault_api_server(vault_orchestrator, auth_manager, config)
        
        # Run server
        uvicorn.run(
            app,
            host=config.get('vault', {}).get('api', {}).get('host', '0.0.0.0'),
            port=config.get('vault', {}).get('api', {}).get('port', 8920),
            log_level="info"
        )


if __name__ == "__main__":
    asyncio.run(main())