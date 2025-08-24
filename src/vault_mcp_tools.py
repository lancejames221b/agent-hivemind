"""
Vault MCP Tools Integration
MCP tools for interacting with the Enterprise Vault Security System.

Author: Lance James, Unit 221B
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import secrets

from .vault.enterprise_vault_orchestrator import EnterpriseVaultOrchestrator
from .memory_server import MemoryMCPServer


class VaultMCPTools:
    """MCP tools for vault operations"""
    
    def __init__(self, vault_orchestrator: EnterpriseVaultOrchestrator,
                 memory_server: MemoryMCPServer):
        self.vault = vault_orchestrator
        self.memory_server = memory_server
        self.logger = logging.getLogger(__name__)
    
    async def get_vault_status(self) -> Dict[str, Any]:
        """Get comprehensive vault status and metrics"""
        try:
            status = await self.vault.get_vault_status()
            
            # Store status check in memory for tracking
            await self.memory_server.store_memory(
                content=json.dumps({
                    'action': 'vault_status_check',
                    'timestamp': datetime.utcnow().isoformat(),
                    'status': status
                }),
                category='infrastructure',
                subcategory='vault_monitoring',
                tags=['vault', 'status_check', 'monitoring'],
                importance=0.6
            )
            
            return {
                'success': True,
                'vault_status': status
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get vault status: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def create_approval_request(self, operation_type: str, operation_details: Dict[str, Any],
                                    requesting_user: str) -> Dict[str, Any]:
        """Create multi-signature approval request"""
        try:
            from .vault.multisig_approval import OperationType
            
            # Convert string to enum
            operation_enum = OperationType(operation_type)
            
            request_id = await self.vault.multisig_approval.create_approval_request(
                operation_type=operation_enum,
                operation_details=operation_details,
                requesting_user=requesting_user
            )
            
            # Store approval request in hAIveMind
            await self.memory_server.store_memory(
                content=json.dumps({
                    'approval_request_id': request_id,
                    'operation_type': operation_type,
                    'requesting_user': requesting_user,
                    'operation_details': operation_details,
                    'created_at': datetime.utcnow().isoformat()
                }),
                category='security',
                subcategory='approval_request',
                tags=['vault', 'approval', 'multisig', operation_type],
                importance=0.8
            )
            
            return {
                'success': True,
                'approval_request_id': request_id,
                'message': f'Approval request created for {operation_type}'
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create approval request: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def approve_request(self, request_id: str, approver_id: str, 
                            signature: str, approve: bool = True,
                            reason: str = "") -> Dict[str, Any]:
        """Submit approval for multi-signature request"""
        try:
            # Convert signature from hex string to bytes
            signature_bytes = bytes.fromhex(signature)
            
            success = await self.vault.multisig_approval.submit_approval(
                request_id=request_id,
                approver_id=approver_id,
                approve=approve,
                signature=signature_bytes,
                reason=reason
            )
            
            # Store approval action in hAIveMind
            await self.memory_server.store_memory(
                content=json.dumps({
                    'approval_action': 'approved' if approve else 'rejected',
                    'request_id': request_id,
                    'approver_id': approver_id,
                    'reason': reason,
                    'timestamp': datetime.utcnow().isoformat(),
                    'success': success
                }),
                category='security',
                subcategory='approval_action',
                tags=['vault', 'approval', 'multisig', 'approved' if approve else 'rejected'],
                importance=0.8
            )
            
            return {
                'success': success,
                'message': f'Request {"approved" if approve else "rejected"} by {approver_id}'
            }
            
        except Exception as e:
            self.logger.error(f"Failed to process approval: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get_pending_approvals(self, user_id: str) -> Dict[str, Any]:
        """Get pending approvals for a user"""
        try:
            pending_approvals = await self.vault.multisig_approval.get_pending_approvals(user_id)
            
            return {
                'success': True,
                'pending_approvals': pending_approvals,
                'count': len(pending_approvals)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get pending approvals: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def escrow_credential(self, credential_id: str, credential_data: Dict[str, Any],
                              owner_id: str, escrow_type: str,
                              business_justification: str,
                              recovery_contacts: List[str] = None) -> Dict[str, Any]:
        """Escrow a credential for business continuity"""
        try:
            from .vault.credential_escrow import EscrowType
            
            escrow_enum = EscrowType(escrow_type)
            
            escrow_id = await self.vault.escrow_system.escrow_credential(
                credential_id=credential_id,
                credential_data=credential_data,
                owner_id=owner_id,
                escrow_type=escrow_enum,
                business_justification=business_justification,
                recovery_contacts=recovery_contacts or []
            )
            
            # Store escrow action in hAIveMind
            await self.memory_server.store_memory(
                content=json.dumps({
                    'escrow_id': escrow_id,
                    'credential_id': credential_id,
                    'owner_id': owner_id,
                    'escrow_type': escrow_type,
                    'business_justification': business_justification,
                    'recovery_contacts': recovery_contacts or [],
                    'created_at': datetime.utcnow().isoformat()
                }),
                category='security',
                subcategory='credential_escrow',
                tags=['vault', 'escrow', 'credential', escrow_type],
                importance=0.8
            )
            
            return {
                'success': True,
                'escrow_id': escrow_id,
                'message': f'Credential {credential_id} escrowed successfully'
            }
            
        except Exception as e:
            self.logger.error(f"Failed to escrow credential: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def initiate_credential_recovery(self, escrow_id: str, requesting_user: str,
                                         recovery_reason: str, business_justification: str,
                                         emergency_override: bool = False) -> Dict[str, Any]:
        """Initiate recovery of escrowed credentials"""
        try:
            from .vault.credential_escrow import RecoveryReason
            
            reason_enum = RecoveryReason(recovery_reason)
            
            recovery_id = await self.vault.escrow_system.initiate_credential_recovery(
                escrow_id=escrow_id,
                requesting_user=requesting_user,
                recovery_reason=reason_enum,
                business_justification=business_justification,
                emergency_override=emergency_override
            )
            
            # Store recovery request in hAIveMind
            await self.memory_server.store_memory(
                content=json.dumps({
                    'recovery_id': recovery_id,
                    'escrow_id': escrow_id,
                    'requesting_user': requesting_user,
                    'recovery_reason': recovery_reason,
                    'business_justification': business_justification,
                    'emergency_override': emergency_override,
                    'initiated_at': datetime.utcnow().isoformat()
                }),
                category='security',
                subcategory='credential_recovery',
                tags=['vault', 'escrow', 'recovery', recovery_reason],
                importance=0.9 if emergency_override else 0.7
            )
            
            return {
                'success': True,
                'recovery_id': recovery_id,
                'message': f'Credential recovery initiated for escrow {escrow_id}'
            }
            
        except Exception as e:
            self.logger.error(f"Failed to initiate recovery: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def create_secret_shares(self, secret_data: str, threshold: int, total_shares: int,
                                 key_id: str, owners: List[str]) -> Dict[str, Any]:
        """Create Shamir's secret shares for distributed key management"""
        try:
            secret_bytes = secret_data.encode('utf-8')
            
            shares = await self.vault.shamir_sharing.create_secret_shares(
                secret=secret_bytes,
                threshold=threshold,
                total_shares=total_shares,
                key_id=key_id,
                owners=owners
            )
            
            # Store share creation in hAIveMind (without sensitive data)
            await self.memory_server.store_memory(
                content=json.dumps({
                    'key_id': key_id,
                    'threshold': threshold,
                    'total_shares': total_shares,
                    'owners': owners,
                    'shares_created': len(shares),
                    'created_at': datetime.utcnow().isoformat()
                }),
                category='security',
                subcategory='secret_sharing',
                tags=['vault', 'shamir', 'secret_sharing', 'key_management'],
                importance=0.9
            )
            
            return {
                'success': True,
                'shares_created': len(shares),
                'key_id': key_id,
                'message': f'Created {len(shares)} shares with threshold {threshold}'
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create secret shares: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get_threat_summary(self) -> Dict[str, Any]:
        """Get threat detection summary"""
        try:
            threat_summary = await self.vault.threat_detection.get_threat_summary()
            
            return {
                'success': True,
                'threat_summary': threat_summary
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get threat summary: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get_siem_status(self) -> Dict[str, Any]:
        """Get SIEM integration status"""
        try:
            siem_status = await self.vault.siem_integration.get_siem_status()
            
            return {
                'success': True,
                'siem_status': siem_status
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get SIEM status: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get_haivemind_status(self) -> Dict[str, Any]:
        """Get hAIveMind integration status"""
        try:
            haivemind_status = await self.vault.haivemind_integration.get_haivemind_status()
            
            return {
                'success': True,
                'haivemind_status': haivemind_status
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get hAIveMind status: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def generate_hsm_key(self, hsm_provider: str, key_type: str = "RSA", 
                             key_size: int = 4096) -> Dict[str, Any]:
        """Generate cryptographic key using HSM"""
        try:
            key_id = await self.vault.security_framework.generate_hsm_key(
                hsm_provider=hsm_provider,
                key_type=key_type,
                key_size=key_size
            )
            
            if key_id:
                # Store key generation event in hAIveMind
                await self.memory_server.store_memory(
                    content=json.dumps({
                        'key_id': key_id,
                        'hsm_provider': hsm_provider,
                        'key_type': key_type,
                        'key_size': key_size,
                        'generated_at': datetime.utcnow().isoformat()
                    }),
                    category='security',
                    subcategory='hsm_key_generation',
                    tags=['vault', 'hsm', 'key_generation', hsm_provider],
                    importance=0.8
                )
                
                return {
                    'success': True,
                    'key_id': key_id,
                    'message': f'HSM key generated successfully on {hsm_provider}'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to generate HSM key'
                }
                
        except Exception as e:
            self.logger.error(f"Failed to generate HSM key: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def create_security_session(self, user_id: str, security_level: str,
                                    duration_hours: int = 8) -> Dict[str, Any]:
        """Create secure session with specified security level"""
        try:
            from .vault.security_framework import SecurityLevel
            
            level_enum = SecurityLevel(security_level)
            
            session_id = await self.vault.security_framework.create_security_session(
                user_id=user_id,
                security_level=level_enum,
                duration_hours=duration_hours
            )
            
            # Store session creation in hAIveMind
            await self.memory_server.store_memory(
                content=json.dumps({
                    'session_id': session_id,
                    'user_id': user_id,
                    'security_level': security_level,
                    'duration_hours': duration_hours,
                    'created_at': datetime.utcnow().isoformat()
                }),
                category='security',
                subcategory='session_management',
                tags=['vault', 'session', 'security_level', user_id],
                importance=0.7
            )
            
            return {
                'success': True,
                'session_id': session_id,
                'expires_in_hours': duration_hours,
                'security_level': security_level
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create security session: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def initiate_collaborative_response(self, threat_category: str,
                                            threat_description: str,
                                            affected_assets: List[str]) -> Dict[str, Any]:
        """Initiate collaborative threat response across hAIveMind network"""
        try:
            from .vault.haivemind_integration import SecurityEventCategory
            
            category_enum = SecurityEventCategory(threat_category)
            
            response_id = await self.vault.haivemind_integration.initiate_collaborative_response(
                threat_category=category_enum,
                threat_description=threat_description,
                affected_assets=affected_assets
            )
            
            # Store collaborative response in hAIveMind
            await self.memory_server.store_memory(
                content=json.dumps({
                    'response_id': response_id,
                    'threat_category': threat_category,
                    'threat_description': threat_description,
                    'affected_assets': affected_assets,
                    'initiated_at': datetime.utcnow().isoformat()
                }),
                category='security',
                subcategory='collaborative_response',
                tags=['vault', 'haivemind', 'threat_response', threat_category],
                importance=0.9
            )
            
            return {
                'success': True,
                'response_id': response_id,
                'message': f'Collaborative response initiated for {threat_category}'
            }
            
        except Exception as e:
            self.logger.error(f"Failed to initiate collaborative response: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get_compliance_report(self, report_date: Optional[str] = None) -> Dict[str, Any]:
        """Get compliance report for specified date"""
        try:
            if not report_date:
                report_date = datetime.utcnow().strftime('%Y-%m-%d')
            
            report_key = f"compliance_report:{report_date}"
            report_data = await self.vault.redis.hgetall(report_key)
            
            if report_data:
                compliance_report = {
                    k.decode() if isinstance(k, bytes) else k: 
                    json.loads(v.decode() if isinstance(v, bytes) else v) if k.decode().endswith(('_status', 'metrics', 'recommendations')) 
                    else v.decode() if isinstance(v, bytes) else v
                    for k, v in report_data.items()
                }
                
                return {
                    'success': True,
                    'compliance_report': compliance_report,
                    'report_date': report_date
                }
            else:
                return {
                    'success': False,
                    'error': f'No compliance report found for {report_date}'
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get compliance report: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def emergency_credential_revocation(self, credential_ids: List[str],
                                            reason: str, authorizing_user: str) -> Dict[str, Any]:
        """Emergency revocation of credentials across all systems"""
        try:
            revoked_credentials = []
            failed_revocations = []
            
            for credential_id in credential_ids:
                try:
                    await self.vault.orchestrator._emergency_revoke_credential(credential_id)
                    revoked_credentials.append(credential_id)
                except Exception as e:
                    failed_revocations.append({'credential_id': credential_id, 'error': str(e)})
            
            # Store emergency revocation in hAIveMind
            await self.memory_server.store_memory(
                content=json.dumps({
                    'revocation_id': secrets.token_hex(16),
                    'credential_ids': credential_ids,
                    'revoked_credentials': revoked_credentials,
                    'failed_revocations': failed_revocations,
                    'reason': reason,
                    'authorizing_user': authorizing_user,
                    'timestamp': datetime.utcnow().isoformat()
                }),
                category='security',
                subcategory='emergency_revocation',
                tags=['vault', 'emergency', 'revocation', 'credentials'],
                importance=0.95
            )
            
            return {
                'success': True,
                'revoked_count': len(revoked_credentials),
                'failed_count': len(failed_revocations),
                'revoked_credentials': revoked_credentials,
                'failed_revocations': failed_revocations
            }
            
        except Exception as e:
            self.logger.error(f"Failed emergency credential revocation: {str(e)}")
            return {'success': False, 'error': str(e)}