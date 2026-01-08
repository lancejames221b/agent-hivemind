"""
Vault Dashboard API Endpoints
FastAPI endpoints specifically for the vault management dashboard interface.

Author: Lance James, Unit 221B
"""

import asyncio
import logging
import json
import csv
import io
import zipfile
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Request, Response, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
import secrets
import hashlib

from .enhanced_vault_api import EnhancedVaultAPI
from .core_vault import CoreVault, CredentialType, RiskLevel
from .audit_manager import AuditManager, AuditEventType
from .haivemind_integration import HAIveMindVaultIntegration
from ..auth import AuthManager
from ..memory_server import MemoryMCPServer

# Initialize logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/vault", tags=["vault-dashboard"])

# Pydantic models for dashboard-specific requests
class VaultUnlockRequest(BaseModel):
    master_password: str = Field(..., description="Master password to unlock vault")
    remember_session: bool = Field(False, description="Remember session for extended period")

class BulkImportRequest(BaseModel):
    credentials: List[Dict[str, Any]] = Field(..., description="List of credentials to import")
    overwrite_existing: bool = Field(False, description="Overwrite existing credentials with same name")
    validate_only: bool = Field(False, description="Only validate data without importing")

class CredentialImpactResponse(BaseModel):
    shared_with_users: int = Field(0, description="Number of users with access")
    dependent_services: int = Field(0, description="Number of dependent services")
    automation_scripts: int = Field(0, description="Number of automation scripts using this credential")
    last_accessed_days: int = Field(999, description="Days since last access")
    risk_level: str = Field("low", description="Risk level of deletion")

class VaultStatsResponse(BaseModel):
    total_credentials: int = Field(0, description="Total number of credentials")
    expiring_credentials: int = Field(0, description="Number of expiring credentials")
    expired_credentials: int = Field(0, description="Number of expired credentials")
    credentials_by_type: Dict[str, int] = Field(default_factory=dict, description="Credentials grouped by type")
    credentials_by_environment: Dict[str, int] = Field(default_factory=dict, description="Credentials grouped by environment")
    recent_activity: List[Dict[str, Any]] = Field(default_factory=list, description="Recent vault activity")
    security_alerts: List[Dict[str, Any]] = Field(default_factory=list, description="Security alerts")

class AuditLogEntry(BaseModel):
    id: str
    timestamp: datetime
    action: str
    resource_type: str
    resource_id: str
    resource_name: str
    user_id: str
    ip_address: str
    user_agent: str
    description: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

# Initialize components
vault_api = None
core_vault = None
audit_manager = None
haivemind_integration = None
auth_manager = None
memory_server = None

def get_vault_components():
    """Get vault components (initialized elsewhere)"""
    global vault_api, core_vault, audit_manager, haivemind_integration, auth_manager, memory_server
    
    if not vault_api:
        # These would be initialized in the main application
        vault_api = EnhancedVaultAPI()
        core_vault = CoreVault()
        audit_manager = AuditManager()
        haivemind_integration = HAIveMindVaultIntegration()
        auth_manager = AuthManager()
        memory_server = MemoryMCPServer()
    
    return vault_api, core_vault, audit_manager, haivemind_integration, auth_manager, memory_server

async def get_current_user(request: Request):
    """Get current authenticated user"""
    _, _, _, _, auth_manager, _ = get_vault_components()
    
    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    
    token = auth_header.split(" ")[1]
    user = await auth_manager.verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user

async def get_vault_session(request: Request):
    """Get vault session token"""
    vault_token = request.headers.get("X-Vault-Token")
    if not vault_token:
        raise HTTPException(status_code=401, detail="Vault session required")
    
    # Verify vault token is valid
    _, core_vault, _, _, _, _ = get_vault_components()
    if not await core_vault.verify_session_token(vault_token):
        raise HTTPException(status_code=401, detail="Invalid or expired vault session")
    
    return vault_token

@router.get("/status", response_model=VaultStatsResponse)
async def get_vault_status(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Get vault status and statistics"""
    try:
        vault_api, core_vault, audit_manager, haivemind_integration, _, memory_server = get_vault_components()
        
        # Get basic stats
        total_credentials = await core_vault.get_credential_count()
        expiring_credentials = await core_vault.get_expiring_credentials_count(days=30)
        expired_credentials = await core_vault.get_expired_credentials_count()
        
        # Get credentials by type and environment
        credentials_by_type = await core_vault.get_credentials_by_type()
        credentials_by_environment = await core_vault.get_credentials_by_environment()
        
        # Get recent activity
        recent_activity = await audit_manager.get_recent_activity(limit=10)
        
        # Get security alerts
        security_alerts = await core_vault.get_security_alerts()
        
        # Store hAIveMind memory
        await haivemind_integration.store_dashboard_interaction({
            'action': 'vault_status_viewed',
            'user_id': current_user['id'],
            'timestamp': datetime.utcnow().isoformat(),
            'stats': {
                'total_credentials': total_credentials,
                'expiring_credentials': expiring_credentials
            }
        })
        
        return VaultStatsResponse(
            total_credentials=total_credentials,
            expiring_credentials=expiring_credentials,
            expired_credentials=expired_credentials,
            credentials_by_type=credentials_by_type,
            credentials_by_environment=credentials_by_environment,
            recent_activity=recent_activity,
            security_alerts=security_alerts
        )
        
    except Exception as e:
        logger.error(f"Error getting vault status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get vault status")

@router.post("/unlock")
async def unlock_vault(
    request: VaultUnlockRequest,
    req: Request,
    current_user: dict = Depends(get_current_user)
):
    """Unlock vault with master password"""
    try:
        vault_api, core_vault, audit_manager, haivemind_integration, _, _ = get_vault_components()
        
        # Verify master password
        if not await core_vault.verify_master_password(request.master_password):
            # Log failed attempt
            await audit_manager.log_event(
                AuditEventType.VAULT_UNLOCK_FAILED,
                user_id=current_user['id'],
                ip_address=req.client.host,
                metadata={'reason': 'invalid_master_password'}
            )
            raise HTTPException(status_code=401, detail="Invalid master password")
        
        # Generate vault session token
        session_duration = 3600 if request.remember_session else 1800  # 1 hour or 30 minutes
        vault_token = await core_vault.create_session_token(
            user_id=current_user['id'],
            duration_seconds=session_duration
        )
        
        # Log successful unlock
        await audit_manager.log_event(
            AuditEventType.VAULT_UNLOCKED,
            user_id=current_user['id'],
            ip_address=req.client.host,
            metadata={
                'remember_session': request.remember_session,
                'session_duration': session_duration
            }
        )
        
        # Store hAIveMind memory
        await haivemind_integration.store_security_event({
            'action': 'vault_unlocked',
            'user_id': current_user['id'],
            'ip_address': req.client.host,
            'timestamp': datetime.utcnow().isoformat(),
            'remember_session': request.remember_session
        })
        
        return {
            "vault_token": vault_token,
            "expires_in": session_duration,
            "message": "Vault unlocked successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unlocking vault: {e}")
        raise HTTPException(status_code=500, detail="Failed to unlock vault")

@router.post("/lock")
async def lock_vault(
    req: Request,
    current_user: dict = Depends(get_current_user),
    vault_token: str = Depends(get_vault_session)
):
    """Lock vault and invalidate session"""
    try:
        vault_api, core_vault, audit_manager, haivemind_integration, _, _ = get_vault_components()
        
        # Invalidate vault session
        await core_vault.invalidate_session_token(vault_token)
        
        # Log vault lock
        await audit_manager.log_event(
            AuditEventType.VAULT_LOCKED,
            user_id=current_user['id'],
            ip_address=req.client.host
        )
        
        # Store hAIveMind memory
        await haivemind_integration.store_security_event({
            'action': 'vault_locked',
            'user_id': current_user['id'],
            'ip_address': req.client.host,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return {"message": "Vault locked successfully"}
        
    except Exception as e:
        logger.error(f"Error locking vault: {e}")
        raise HTTPException(status_code=500, detail="Failed to lock vault")

@router.get("/credentials/{credential_id}/impact", response_model=CredentialImpactResponse)
async def get_credential_deletion_impact(
    credential_id: str,
    current_user: dict = Depends(get_current_user),
    vault_token: str = Depends(get_vault_session)
):
    """Get impact analysis for credential deletion"""
    try:
        vault_api, core_vault, audit_manager, haivemind_integration, _, _ = get_vault_components()
        
        # Get credential
        credential = await core_vault.get_credential(credential_id)
        if not credential:
            raise HTTPException(status_code=404, detail="Credential not found")
        
        # Analyze impact
        impact = await core_vault.analyze_deletion_impact(credential_id)
        
        # Store hAIveMind memory
        await haivemind_integration.store_dashboard_interaction({
            'action': 'deletion_impact_analyzed',
            'user_id': current_user['id'],
            'credential_id': credential_id,
            'timestamp': datetime.utcnow().isoformat(),
            'impact': impact
        })
        
        return CredentialImpactResponse(**impact)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing deletion impact: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze deletion impact")

@router.post("/credentials/bulk-import")
async def bulk_import_credentials(
    request: BulkImportRequest,
    req: Request,
    current_user: dict = Depends(get_current_user),
    vault_token: str = Depends(get_vault_session)
):
    """Bulk import credentials"""
    try:
        vault_api, core_vault, audit_manager, haivemind_integration, _, _ = get_vault_components()
        
        if request.validate_only:
            # Validate only
            validation_results = []
            for i, credential_data in enumerate(request.credentials):
                try:
                    await core_vault.validate_credential_data(credential_data)
                    validation_results.append({"index": i, "valid": True})
                except Exception as e:
                    validation_results.append({"index": i, "valid": False, "error": str(e)})
            
            return {"validation_results": validation_results}
        
        # Import credentials
        imported = 0
        failed = 0
        errors = []
        
        for i, credential_data in enumerate(request.credentials):
            try:
                # Add metadata
                credential_data['created_by'] = current_user['id']
                credential_data['created_at'] = datetime.utcnow().isoformat()
                
                # Check if credential exists
                existing = await core_vault.find_credential_by_name(
                    credential_data['name'],
                    credential_data['environment']
                )
                
                if existing and not request.overwrite_existing:
                    errors.append(f"Row {i+1}: Credential already exists")
                    failed += 1
                    continue
                
                # Create or update credential
                if existing and request.overwrite_existing:
                    await core_vault.update_credential(existing['id'], credential_data)
                else:
                    await core_vault.create_credential(credential_data)
                
                imported += 1
                
            except Exception as e:
                errors.append(f"Row {i+1}: {str(e)}")
                failed += 1
        
        # Log bulk import
        await audit_manager.log_event(
            AuditEventType.BULK_IMPORT,
            user_id=current_user['id'],
            ip_address=req.client.host,
            metadata={
                'imported': imported,
                'failed': failed,
                'total': len(request.credentials)
            }
        )
        
        # Store hAIveMind memory
        await haivemind_integration.store_dashboard_interaction({
            'action': 'bulk_import_completed',
            'user_id': current_user['id'],
            'timestamp': datetime.utcnow().isoformat(),
            'imported': imported,
            'failed': failed,
            'total': len(request.credentials)
        })
        
        return {
            "imported": imported,
            "failed": failed,
            "total": len(request.credentials),
            "errors": errors if errors else None
        }
        
    except Exception as e:
        logger.error(f"Error during bulk import: {e}")
        raise HTTPException(status_code=500, detail="Bulk import failed")

@router.get("/credentials/export")
async def export_credentials(
    format: str = "json",
    req: Request = None,
    current_user: dict = Depends(get_current_user),
    vault_token: str = Depends(get_vault_session)
):
    """Export credentials in various formats"""
    try:
        vault_api, core_vault, audit_manager, haivemind_integration, _, _ = get_vault_components()
        
        # Get all credentials (without sensitive data for export)
        credentials = await core_vault.get_all_credentials_metadata()
        
        if format == "json":
            # Export as JSON
            export_data = json.dumps(credentials, indent=2, default=str)
            
            # Log export
            await audit_manager.log_event(
                AuditEventType.EXPORT,
                user_id=current_user['id'],
                ip_address=req.client.host if req else "unknown",
                metadata={'format': 'json', 'count': len(credentials)}
            )
            
            return StreamingResponse(
                io.StringIO(export_data),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename=credentials-export-{datetime.now().strftime('%Y%m%d')}.json"}
            )
            
        elif format == "csv":
            # Export as CSV
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=[
                'name', 'credential_type', 'environment', 'service', 
                'description', 'created_at', 'expires_at', 'tags'
            ])
            writer.writeheader()
            
            for credential in credentials:
                row = {
                    'name': credential.get('name', ''),
                    'credential_type': credential.get('credential_type', ''),
                    'environment': credential.get('environment', ''),
                    'service': credential.get('service', ''),
                    'description': credential.get('description', ''),
                    'created_at': credential.get('created_at', ''),
                    'expires_at': credential.get('expires_at', ''),
                    'tags': ', '.join(credential.get('tags', []))
                }
                writer.writerow(row)
            
            # Log export
            await audit_manager.log_event(
                AuditEventType.EXPORT,
                user_id=current_user['id'],
                ip_address=req.client.host if req else "unknown",
                metadata={'format': 'csv', 'count': len(credentials)}
            )
            
            return StreamingResponse(
                io.StringIO(output.getvalue()),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=credentials-export-{datetime.now().strftime('%Y%m%d')}.csv"}
            )
            
        elif format == "encrypted":
            # Export as encrypted ZIP
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add JSON data to ZIP
                export_data = json.dumps(credentials, indent=2, default=str)
                zip_file.writestr(f"credentials-export-{datetime.now().strftime('%Y%m%d')}.json", export_data)
                
                # Add README with instructions
                readme_content = """
Credential Vault Export
======================

This archive contains exported credential metadata from the hAIveMind Credential Vault.

SECURITY NOTICE:
- This file contains sensitive information
- Store in a secure location
- Delete after use if no longer needed
- Do not share via unsecured channels

Export Details:
- Export Date: {export_date}
- Exported By: {user_id}
- Total Credentials: {count}
- Format: JSON

The JSON file contains credential metadata but not the actual credential values for security.
""".format(
                    export_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
                    user_id=current_user['id'],
                    count=len(credentials)
                )
                zip_file.writestr("README.txt", readme_content)
            
            # Log export
            await audit_manager.log_event(
                AuditEventType.EXPORT,
                user_id=current_user['id'],
                ip_address=req.client.host if req else "unknown",
                metadata={'format': 'encrypted', 'count': len(credentials)}
            )
            
            zip_buffer.seek(0)
            return StreamingResponse(
                io.BytesIO(zip_buffer.read()),
                media_type="application/zip",
                headers={"Content-Disposition": f"attachment; filename=credentials-export-{datetime.now().strftime('%Y%m%d')}.zip"}
            )
            
        else:
            raise HTTPException(status_code=400, detail="Unsupported export format")
            
        # Store hAIveMind memory
        await haivemind_integration.store_dashboard_interaction({
            'action': 'credentials_exported',
            'user_id': current_user['id'],
            'timestamp': datetime.utcnow().isoformat(),
            'format': format,
            'count': len(credentials)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting credentials: {e}")
        raise HTTPException(status_code=500, detail="Export failed")

@router.get("/audit-log", response_model=List[AuditLogEntry])
async def get_audit_log(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    vault_token: str = Depends(get_vault_session)
):
    """Get vault audit log"""
    try:
        vault_api, core_vault, audit_manager, haivemind_integration, _, _ = get_vault_components()
        
        # Parse date filters
        date_from_dt = None
        date_to_dt = None
        
        if date_from:
            date_from_dt = datetime.fromisoformat(date_from)
        if date_to:
            date_to_dt = datetime.fromisoformat(date_to)
        
        # Get audit log entries
        entries = await audit_manager.get_audit_log(
            date_from=date_from_dt,
            date_to=date_to_dt,
            action=action,
            limit=limit,
            offset=offset
        )
        
        # Store hAIveMind memory
        await haivemind_integration.store_dashboard_interaction({
            'action': 'audit_log_viewed',
            'user_id': current_user['id'],
            'timestamp': datetime.utcnow().isoformat(),
            'filters': {
                'date_from': date_from,
                'date_to': date_to,
                'action': action
            },
            'result_count': len(entries)
        })
        
        return [AuditLogEntry(**entry) for entry in entries]
        
    except Exception as e:
        logger.error(f"Error getting audit log: {e}")
        raise HTTPException(status_code=500, detail="Failed to get audit log")

@router.post("/credentials/{credential_id}/rotate")
async def rotate_credential(
    credential_id: str,
    req: Request,
    current_user: dict = Depends(get_current_user),
    vault_token: str = Depends(get_vault_session)
):
    """Rotate credential"""
    try:
        vault_api, core_vault, audit_manager, haivemind_integration, _, _ = get_vault_components()
        
        # Get credential
        credential = await core_vault.get_credential(credential_id)
        if not credential:
            raise HTTPException(status_code=404, detail="Credential not found")
        
        # Rotate credential
        rotation_result = await core_vault.rotate_credential(credential_id)
        
        # Log rotation (SECURITY: Only log version numbers, NEVER log old/new credential values)
        await audit_manager.log_event(
            AuditEventType.CREDENTIAL_ROTATED,
            user_id=current_user['id'],
            ip_address=req.client.host,
            resource_id=credential_id,
            resource_name=credential['name'],
            metadata={
                'rotation_method': rotation_result.get('method', 'manual'),
                'previous_version': rotation_result.get('previous_version'),  # Version number only, safe
                'new_version': rotation_result.get('new_version')  # Version number only, safe
                # DO NOT LOG: old_credential, new_credential, credential_data
            }
        )
        
        # Store hAIveMind memory
        await haivemind_integration.store_dashboard_interaction({
            'action': 'credential_rotated',
            'user_id': current_user['id'],
            'credential_id': credential_id,
            'timestamp': datetime.utcnow().isoformat(),
            'rotation_result': rotation_result
        })
        
        return {
            "message": "Credential rotated successfully",
            "rotation_method": rotation_result.get('method', 'manual'),
            "new_version": rotation_result.get('new_version')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rotating credential: {e}")
        raise HTTPException(status_code=500, detail="Failed to rotate credential")

@router.get("/stats", response_model=VaultStatsResponse)
async def get_vault_stats(
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive vault statistics"""
    try:
        vault_api, core_vault, audit_manager, haivemind_integration, _, _ = get_vault_components()
        
        # This is a simplified version - would be expanded with actual stats
        stats = VaultStatsResponse(
            total_credentials=0,
            expiring_credentials=0,
            expired_credentials=0,
            credentials_by_type={},
            credentials_by_environment={},
            recent_activity=[],
            security_alerts=[]
        )
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting vault stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get vault stats")

# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check for vault dashboard API"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

# Error handlers
@router.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url)
        }
    )

@router.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception in vault dashboard API: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url)
        }
    )