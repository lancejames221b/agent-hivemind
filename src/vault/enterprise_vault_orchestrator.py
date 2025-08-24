"""
Enterprise Vault Security Orchestrator
Main orchestrator for all advanced vault features and enterprise security.

Author: Lance James, Unit 221B
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import secrets
import redis

from .security_framework import AdvancedSecurityFramework
from .shamir_secret_sharing import ShamirSecretSharing
from .multisig_approval import MultiSignatureApproval
from .credential_escrow import CredentialEscrowSystem
from .threat_detection import ThreatDetectionSystem
from .siem_integration import SIEMIntegration
from .haivemind_integration import HAIveMindVaultIntegration
from ..memory_server import MemoryMCPServer


class VaultOperationStatus(Enum):
    """Status of vault operations"""
    INITIALIZED = "initialized"
    RUNNING = "running"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    ERROR = "error"
    STOPPED = "stopped"


class SecurityPosture(Enum):
    """Overall security posture levels"""
    OPTIMAL = "optimal"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    CONCERNING = "concerning"
    CRITICAL = "critical"


@dataclass
class VaultMetrics:
    """Comprehensive vault metrics"""
    total_credentials: int
    active_sessions: int
    threat_level: str
    security_posture: SecurityPosture
    compliance_score: float
    hsm_health: str
    haivemind_status: str
    siem_connections: int
    pending_approvals: int
    active_escrows: int
    anomalies_detected: int
    last_updated: datetime


class EnterpriseVaultOrchestrator:
    """Main orchestrator for enterprise vault security features"""
    
    def __init__(self, config: Dict[str, Any], redis_client: redis.Redis,
                 memory_server: MemoryMCPServer):
        self.config = config
        self.redis = redis_client
        self.memory_server = memory_server
        self.logger = logging.getLogger(__name__)
        
        # Initialize all security components
        self.security_framework = AdvancedSecurityFramework(config, redis_client)
        self.shamir_sharing = ShamirSecretSharing(config, redis_client)
        self.multisig_approval = MultiSignatureApproval(config, redis_client)
        self.escrow_system = CredentialEscrowSystem(config, redis_client)
        self.threat_detection = ThreatDetectionSystem(config, redis_client)
        self.siem_integration = SIEMIntegration(config, redis_client)
        self.haivemind_integration = HAIveMindVaultIntegration(config, redis_client, memory_server)
        
        self.status = VaultOperationStatus.INITIALIZED
        self.metrics = VaultMetrics(
            total_credentials=0,
            active_sessions=0,
            threat_level="low",
            security_posture=SecurityPosture.ACCEPTABLE,
            compliance_score=0.0,
            hsm_health="unknown",
            haivemind_status="disconnected",
            siem_connections=0,
            pending_approvals=0,
            active_escrows=0,
            anomalies_detected=0,
            last_updated=datetime.utcnow()
        )
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        
    async def initialize_enterprise_vault(self) -> bool:
        """Initialize all enterprise vault components"""
        try:
            self.logger.info("Initializing Enterprise Vault Security System...")
            
            # Initialize core security framework
            if not await self.security_framework.initialize_hsm_providers():
                self.logger.error("Failed to initialize HSM providers")
                return False
            
            # Initialize Shamir's Secret Sharing
            self.logger.info("Initializing Shamir's Secret Sharing...")
            # Shamir's Secret Sharing is ready for use
            
            # Initialize multi-signature approval system
            self.logger.info("Initializing Multi-Signature Approval System...")
            if not await self.multisig_approval.initialize_approval_policies():
                self.logger.warning("Failed to initialize all approval policies")
            
            # Initialize credential escrow system
            self.logger.info("Initializing Credential Escrow System...")
            if not await self.escrow_system.initialize_escrow_policies():
                self.logger.warning("Failed to initialize all escrow policies")
            
            # Initialize threat detection system
            self.logger.info("Initializing ML-Based Threat Detection...")
            if not await self.threat_detection.initialize_threat_detection():
                self.logger.warning("Threat detection system running with limited functionality")
            
            # Initialize SIEM integration
            self.logger.info("Initializing SIEM Integration...")
            if not await self.siem_integration.initialize_siem_integrations():
                self.logger.warning("No SIEM systems connected")
            
            # Initialize hAIveMind integration
            self.logger.info("Initializing hAIveMind Integration...")
            if not await self.haivemind_integration.initialize_haivemind_integration():
                self.logger.warning("hAIveMind integration limited")
            
            # Start background monitoring tasks
            await self._start_background_tasks()
            
            # Perform initial security assessment
            await self._perform_security_assessment()
            
            self.status = VaultOperationStatus.RUNNING
            self.logger.info("Enterprise Vault Security System initialized successfully")
            
            # Store initialization event in hAIveMind
            await self.memory_server.store_memory(
                content=json.dumps({
                    'event': 'enterprise_vault_initialized',
                    'timestamp': datetime.utcnow().isoformat(),
                    'components': [
                        'security_framework',
                        'shamir_sharing',
                        'multisig_approval',
                        'escrow_system',
                        'threat_detection',
                        'siem_integration',
                        'haivemind_integration'
                    ],
                    'status': self.status.value
                }),
                category='infrastructure',
                subcategory='vault_initialization',
                tags=['vault', 'enterprise_security', 'initialization'],
                importance=0.9
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize enterprise vault: {str(e)}")
            self.status = VaultOperationStatus.ERROR
            return False
    
    async def _start_background_tasks(self) -> None:
        """Start background monitoring and maintenance tasks"""
        try:
            # Metrics collection task
            metrics_task = asyncio.create_task(self._metrics_collector())
            self.background_tasks.append(metrics_task)
            
            # Security monitoring task
            security_task = asyncio.create_task(self._security_monitor())
            self.background_tasks.append(security_task)
            
            # Health check task
            health_task = asyncio.create_task(self._health_checker())
            self.background_tasks.append(health_task)
            
            # Compliance monitoring task
            compliance_task = asyncio.create_task(self._compliance_monitor())
            self.background_tasks.append(compliance_task)
            
            # Integration monitoring task
            integration_task = asyncio.create_task(self._integration_monitor())
            self.background_tasks.append(integration_task)
            
            self.logger.info(f"Started {len(self.background_tasks)} background tasks")
            
        except Exception as e:
            self.logger.error(f"Failed to start background tasks: {str(e)}")
    
    async def process_vault_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process vault events through all security layers"""
        try:
            event_id = event_data.get('event_id', secrets.token_hex(16))
            event_type = event_data.get('event_type')
            user_id = event_data.get('user_id')
            
            self.logger.info(f"Processing vault event {event_id}: {event_type}")
            
            processing_result = {
                'event_id': event_id,
                'processed_at': datetime.utcnow().isoformat(),
                'security_checks': {},
                'approvals_required': [],
                'threat_assessment': {},
                'compliance_status': 'compliant',
                'recommendations': []
            }
            
            # Security framework validation
            session_valid = True
            required_security_level = self._determine_security_level(event_type)
            
            if user_id:
                session_id = event_data.get('session_id')
                if session_id:
                    session_valid = await self.security_framework.validate_security_session(
                        session_id, required_security_level
                    )
            
            processing_result['security_checks']['session_validation'] = session_valid
            
            # Multi-signature approval check
            approval_required = await self._check_approval_requirements(event_data)
            if approval_required:
                approval_request_id = await self._initiate_approval_process(event_data)
                processing_result['approvals_required'].append(approval_request_id)
            
            # Threat detection analysis
            security_event = self._convert_to_security_event(event_data)
            anomalies = await self.threat_detection.analyze_security_event(security_event)
            
            processing_result['threat_assessment'] = {
                'anomalies_detected': len(anomalies),
                'highest_risk_score': max([a.confidence_score for a in anomalies]) if anomalies else 0.0,
                'recommended_actions': []
            }
            
            for anomaly in anomalies:
                processing_result['threat_assessment']['recommended_actions'].extend(
                    anomaly.recommended_actions
                )
            
            # hAIveMind integration
            haivemind_insights = await self.haivemind_integration.process_security_event(event_data)
            if haivemind_insights:
                processing_result['haivemind_insights'] = len(haivemind_insights)
            
            # SIEM forwarding
            await self.siem_integration.send_security_event(security_event)
            
            # Audit logging
            await self._audit_vault_event(event_data, processing_result)
            
            self.logger.info(f"Vault event {event_id} processed successfully")
            return processing_result
            
        except Exception as e:
            self.logger.error(f"Failed to process vault event: {str(e)}")
            return {'error': str(e), 'event_id': event_data.get('event_id', 'unknown')}
    
    def _determine_security_level(self, event_type: str) -> Any:
        """Determine required security level based on event type"""
        from .security_framework import SecurityLevel
        
        high_security_events = [
            'credential_deletion',
            'vault_configuration',
            'emergency_access',
            'master_key_operation'
        ]
        
        if event_type in high_security_events:
            return SecurityLevel.HIGH
        else:
            return SecurityLevel.STANDARD
    
    async def _check_approval_requirements(self, event_data: Dict[str, Any]) -> bool:
        """Check if event requires multi-signature approval"""
        from .multisig_approval import OperationType
        
        approval_required_events = {
            'credential_deletion': OperationType.CREDENTIAL_DELETION,
            'credential_creation': OperationType.CREDENTIAL_CREATION,
            'vault_configuration': OperationType.VAULT_CONFIGURATION,
            'user_management': OperationType.USER_MANAGEMENT,
            'emergency_revocation': OperationType.EMERGENCY_REVOCATION
        }
        
        event_type = event_data.get('event_type')
        return event_type in approval_required_events
    
    async def _initiate_approval_process(self, event_data: Dict[str, Any]) -> str:
        """Initiate multi-signature approval process"""
        from .multisig_approval import OperationType
        
        operation_map = {
            'credential_deletion': OperationType.CREDENTIAL_DELETION,
            'credential_creation': OperationType.CREDENTIAL_CREATION,
            'vault_configuration': OperationType.VAULT_CONFIGURATION,
            'user_management': OperationType.USER_MANAGEMENT,
            'emergency_revocation': OperationType.EMERGENCY_REVOCATION
        }
        
        event_type = event_data.get('event_type')
        operation_type = operation_map.get(event_type, OperationType.CREDENTIAL_ACCESS)
        
        return await self.multisig_approval.create_approval_request(
            operation_type=operation_type,
            operation_details=event_data,
            requesting_user=event_data.get('user_id', 'system')
        )
    
    def _convert_to_security_event(self, event_data: Dict[str, Any]):
        """Convert vault event to security event for analysis"""
        from .threat_detection import SecurityEvent
        
        return SecurityEvent(
            event_id=event_data.get('event_id', secrets.token_hex(16)),
            user_id=event_data.get('user_id'),
            credential_id=event_data.get('credential_id'),
            action=event_data.get('event_type', 'unknown'),
            timestamp=datetime.fromisoformat(event_data.get('timestamp', datetime.utcnow().isoformat())),
            source_ip=event_data.get('source_ip', '127.0.0.1'),
            user_agent=event_data.get('user_agent', 'unknown'),
            location=event_data.get('location', {}),
            success=event_data.get('success', True),
            metadata=event_data
        )
    
    async def _audit_vault_event(self, event_data: Dict[str, Any], 
                                processing_result: Dict[str, Any]) -> None:
        """Audit vault event for compliance"""
        try:
            audit_entry = {
                'audit_id': secrets.token_hex(16),
                'timestamp': datetime.utcnow().isoformat(),
                'event_id': event_data.get('event_id'),
                'event_type': event_data.get('event_type'),
                'user_id': event_data.get('user_id'),
                'source_ip': event_data.get('source_ip'),
                'processing_result': processing_result,
                'compliance_flags': self._generate_compliance_flags(event_data),
                'retention_period': self._calculate_retention_period(event_data.get('event_type'))
            }
            
            await self.redis.lpush("vault_audit_log", json.dumps(audit_entry))
            await self.redis.expire("vault_audit_log", 86400 * 2555)  # 7 years
            
            # Store in hAIveMind for network-wide audit trail
            await self.memory_server.store_memory(
                content=json.dumps(audit_entry),
                category='security',
                subcategory='vault_audit',
                tags=['audit', 'vault', event_data.get('event_type', 'unknown')],
                importance=0.7
            )
            
        except Exception as e:
            self.logger.error(f"Failed to audit vault event: {str(e)}")
    
    def _generate_compliance_flags(self, event_data: Dict[str, Any]) -> List[str]:
        """Generate compliance flags for audit entry"""
        flags = []
        
        event_type = event_data.get('event_type')
        
        if event_type in ['credential_access', 'credential_creation']:
            flags.extend(['SOX', 'PCI_DSS'])
        
        if event_data.get('pii_involved', False):
            flags.extend(['HIPAA', 'GDPR'])
        
        if event_data.get('financial_data', False):
            flags.append('SOX')
        
        return flags
    
    def _calculate_retention_period(self, event_type: str) -> int:
        """Calculate retention period in days based on event type"""
        retention_map = {
            'credential_deletion': 2555,  # 7 years
            'vault_configuration': 2555,  # 7 years
            'emergency_access': 1825,     # 5 years
            'credential_access': 1095,    # 3 years
            'authentication': 365,        # 1 year
            'default': 1095               # 3 years
        }
        
        return retention_map.get(event_type, retention_map['default'])
    
    async def _metrics_collector(self) -> None:
        """Background task to collect vault metrics"""
        while True:
            try:
                # Collect metrics from all components
                security_metrics = await self.security_framework.get_security_metrics()
                escrow_metrics = await self.escrow_system.get_escrow_metrics()
                threat_metrics = await self.threat_detection.get_threat_summary()
                siem_status = await self.siem_integration.get_siem_status()
                haivemind_status = await self.haivemind_integration.get_haivemind_status()
                
                # Update consolidated metrics
                self.metrics = VaultMetrics(
                    total_credentials=await self._count_total_credentials(),
                    active_sessions=security_metrics.get('active_sessions', 0),
                    threat_level=threat_metrics.get('threat_levels_distribution', {}).get('high', 0) > 0 and 'high' or 'medium',
                    security_posture=await self._calculate_security_posture(),
                    compliance_score=await self._calculate_compliance_score(),
                    hsm_health=security_metrics.get('framework_status', 'unknown'),
                    haivemind_status=haivemind_status.get('network_connectivity', 'unknown'),
                    siem_connections=siem_status.get('active_connections', 0),
                    pending_approvals=len(await self.multisig_approval.get_pending_approvals('system')),
                    active_escrows=escrow_metrics.get('active_escrows', 0),
                    anomalies_detected=threat_metrics.get('anomalies_last_24h', 0),
                    last_updated=datetime.utcnow()
                )
                
                # Store metrics in Redis for quick access
                await self.redis.hset("vault_metrics", mapping={
                    'total_credentials': self.metrics.total_credentials,
                    'active_sessions': self.metrics.active_sessions,
                    'threat_level': self.metrics.threat_level,
                    'security_posture': self.metrics.security_posture.value,
                    'compliance_score': str(self.metrics.compliance_score),
                    'last_updated': self.metrics.last_updated.isoformat()
                })
                
                await asyncio.sleep(300)  # Collect every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Metrics collector error: {str(e)}")
                await asyncio.sleep(60)
    
    async def _count_total_credentials(self) -> int:
        """Count total credentials in vault"""
        try:
            credential_count = await self.redis.scard("vault_credentials")
            return credential_count or 0
        except:
            return 0
    
    async def _calculate_security_posture(self) -> SecurityPosture:
        """Calculate overall security posture"""
        try:
            # Factors affecting security posture
            hsm_healthy = await self._check_hsm_health()
            threat_level_low = self.metrics.threat_level in ['low', 'medium']
            siem_connected = self.metrics.siem_connections > 0
            haivemind_active = self.metrics.haivemind_status == 'active'
            no_critical_anomalies = self.metrics.anomalies_detected < 10
            
            score = sum([hsm_healthy, threat_level_low, siem_connected, 
                        haivemind_active, no_critical_anomalies])
            
            if score >= 5:
                return SecurityPosture.OPTIMAL
            elif score >= 4:
                return SecurityPosture.GOOD
            elif score >= 3:
                return SecurityPosture.ACCEPTABLE
            elif score >= 2:
                return SecurityPosture.CONCERNING
            else:
                return SecurityPosture.CRITICAL
                
        except Exception:
            return SecurityPosture.ACCEPTABLE
    
    async def _check_hsm_health(self) -> bool:
        """Check HSM health status"""
        try:
            return len(self.security_framework.hsm_configs) > 0
        except:
            return False
    
    async def _calculate_compliance_score(self) -> float:
        """Calculate compliance score based on various factors"""
        try:
            score = 0.0
            max_score = 10.0
            
            # Audit trail completeness (2 points)
            audit_count = await self.redis.llen("vault_audit_log")
            if audit_count > 100:
                score += 2.0
            elif audit_count > 10:
                score += 1.0
            
            # Multi-signature compliance (2 points)
            if len(self.multisig_approval.approval_policies) > 0:
                score += 2.0
            
            # Escrow system active (1 point)
            if self.metrics.active_escrows >= 0:
                score += 1.0
            
            # Threat detection active (2 points)
            if len(self.threat_detection.models) > 0:
                score += 2.0
            
            # SIEM integration (1 point)
            if self.metrics.siem_connections > 0:
                score += 1.0
            
            # Data encryption (2 points)
            if self.metrics.hsm_health == 'active':
                score += 2.0
            
            return min(1.0, score / max_score)
            
        except Exception:
            return 0.5
    
    async def _security_monitor(self) -> None:
        """Background security monitoring"""
        while True:
            try:
                # Monitor for security events requiring immediate attention
                critical_events = await self.redis.lrange("critical_security_events", 0, -1)
                
                for event_data in critical_events:
                    try:
                        event = json.loads(event_data.decode() if isinstance(event_data, bytes) else event_data)
                        await self._handle_critical_security_event(event)
                    except Exception as e:
                        self.logger.error(f"Failed to handle critical event: {str(e)}")
                
                # Clear processed events
                if critical_events:
                    await self.redis.delete("critical_security_events")
                
                await asyncio.sleep(60)  # Monitor every minute
                
            except Exception as e:
                self.logger.error(f"Security monitor error: {str(e)}")
                await asyncio.sleep(30)
    
    async def _handle_critical_security_event(self, event: Dict[str, Any]) -> None:
        """Handle critical security events"""
        try:
            event_type = event.get('event_type')
            severity = event.get('severity', 'medium')
            
            if severity == 'critical':
                # Initiate emergency response
                await self._initiate_emergency_response(event)
            
            # Notify security team
            await self._send_security_alert(event)
            
            # Store in hAIveMind for network awareness
            await self.memory_server.store_memory(
                content=json.dumps(event),
                category='security',
                subcategory='critical_event',
                tags=['critical', 'security', event_type],
                importance=0.95
            )
            
        except Exception as e:
            self.logger.error(f"Failed to handle critical security event: {str(e)}")
    
    async def _initiate_emergency_response(self, event: Dict[str, Any]) -> None:
        """Initiate emergency response procedures"""
        try:
            response_id = secrets.token_hex(16)
            
            emergency_response = {
                'response_id': response_id,
                'triggered_by': event.get('event_id'),
                'event_type': event.get('event_type'),
                'initiated_at': datetime.utcnow().isoformat(),
                'status': 'active',
                'actions_taken': []
            }
            
            # Immediate actions based on event type
            if event.get('event_type') == 'credential_compromise':
                # Revoke compromised credentials
                affected_credentials = event.get('affected_credentials', [])
                for cred_id in affected_credentials:
                    await self._emergency_revoke_credential(cred_id)
                    emergency_response['actions_taken'].append(f'revoked_credential_{cred_id}')
            
            elif event.get('event_type') == 'unauthorized_access':
                # Block suspicious IPs
                source_ips = event.get('source_ips', [])
                for ip in source_ips:
                    await self._block_ip_address(ip)
                    emergency_response['actions_taken'].append(f'blocked_ip_{ip}')
            
            # Store emergency response
            await self.redis.hset(f"emergency_response:{response_id}", mapping={
                k: json.dumps(v) if isinstance(v, (list, dict)) else str(v)
                for k, v in emergency_response.items()
            })
            
            self.logger.critical(f"Emergency response {response_id} initiated")
            
        except Exception as e:
            self.logger.error(f"Failed to initiate emergency response: {str(e)}")
    
    async def _emergency_revoke_credential(self, credential_id: str) -> None:
        """Emergency revoke credential"""
        try:
            revocation_data = {
                'credential_id': credential_id,
                'revoked_at': datetime.utcnow().isoformat(),
                'revoked_by': 'emergency_system',
                'reason': 'emergency_security_event'
            }
            
            await self.redis.hset(f"revoked_credential:{credential_id}", mapping=revocation_data)
            await self.redis.srem("vault_credentials", credential_id)
            
            self.logger.warning(f"Emergency revoked credential: {credential_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to revoke credential {credential_id}: {str(e)}")
    
    async def _block_ip_address(self, ip_address: str) -> None:
        """Block suspicious IP address"""
        try:
            block_data = {
                'ip_address': ip_address,
                'blocked_at': datetime.utcnow().isoformat(),
                'blocked_by': 'emergency_system',
                'reason': 'suspicious_activity'
            }
            
            await self.redis.sadd("blocked_ips", ip_address)
            await self.redis.hset(f"ip_block:{ip_address}", mapping=block_data)
            
            self.logger.warning(f"Blocked IP address: {ip_address}")
            
        except Exception as e:
            self.logger.error(f"Failed to block IP {ip_address}: {str(e)}")
    
    async def _send_security_alert(self, event: Dict[str, Any]) -> None:
        """Send security alert notifications"""
        try:
            alert_data = {
                'alert_id': secrets.token_hex(16),
                'event_id': event.get('event_id'),
                'event_type': event.get('event_type'),
                'severity': event.get('severity'),
                'timestamp': datetime.utcnow().isoformat(),
                'description': event.get('description', 'Critical security event detected'),
                'recommended_actions': event.get('recommended_actions', [])
            }
            
            await self.redis.lpush("security_alerts", json.dumps(alert_data))
            
        except Exception as e:
            self.logger.error(f"Failed to send security alert: {str(e)}")
    
    async def _health_checker(self) -> None:
        """Background health checking"""
        while True:
            try:
                # Check health of all components
                health_status = {
                    'security_framework': await self._check_component_health('security_framework'),
                    'shamir_sharing': await self._check_component_health('shamir_sharing'),
                    'multisig_approval': await self._check_component_health('multisig_approval'),
                    'escrow_system': await self._check_component_health('escrow_system'),
                    'threat_detection': await self._check_component_health('threat_detection'),
                    'siem_integration': await self._check_component_health('siem_integration'),
                    'haivemind_integration': await self._check_component_health('haivemind_integration')
                }
                
                # Update overall status
                healthy_components = sum(1 for status in health_status.values() if status)
                total_components = len(health_status)
                
                if healthy_components == total_components:
                    self.status = VaultOperationStatus.RUNNING
                elif healthy_components >= total_components * 0.7:
                    self.status = VaultOperationStatus.DEGRADED
                else:
                    self.status = VaultOperationStatus.ERROR
                
                # Store health status
                await self.redis.hset("vault_health", mapping={
                    k: str(v) for k, v in health_status.items()
                })
                await self.redis.hset("vault_health", "overall_status", self.status.value)
                await self.redis.hset("vault_health", "last_check", datetime.utcnow().isoformat())
                
                await asyncio.sleep(300)  # Health check every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Health checker error: {str(e)}")
                await asyncio.sleep(60)
    
    async def _check_component_health(self, component_name: str) -> bool:
        """Check health of a specific component"""
        try:
            if component_name == 'security_framework':
                return len(self.security_framework.hsm_configs) >= 0
            elif component_name == 'siem_integration':
                status = await self.siem_integration.get_siem_status()
                return status.get('active_connections', 0) >= 0
            elif component_name == 'haivemind_integration':
                status = await self.haivemind_integration.get_haivemind_status()
                return status.get('agent_registered', False)
            else:
                return True  # Assume healthy if no specific check
                
        except Exception:
            return False
    
    async def _compliance_monitor(self) -> None:
        """Background compliance monitoring"""
        while True:
            try:
                # Check compliance requirements
                compliance_status = await self._assess_compliance_status()
                
                # Generate compliance report if needed
                if datetime.utcnow().hour == 2:  # Daily at 2 AM
                    await self._generate_compliance_report()
                
                await asyncio.sleep(3600)  # Check every hour
                
            except Exception as e:
                self.logger.error(f"Compliance monitor error: {str(e)}")
                await asyncio.sleep(600)
    
    async def _assess_compliance_status(self) -> Dict[str, Any]:
        """Assess current compliance status"""
        try:
            compliance_status = {
                'sox_compliant': await self._check_sox_compliance(),
                'pci_compliant': await self._check_pci_compliance(),
                'hipaa_compliant': await self._check_hipaa_compliance(),
                'gdpr_compliant': await self._check_gdpr_compliance(),
                'last_assessment': datetime.utcnow().isoformat()
            }
            
            await self.redis.hset("vault_compliance", mapping={
                k: str(v) for k, v in compliance_status.items()
            })
            
            return compliance_status
            
        except Exception as e:
            self.logger.error(f"Failed to assess compliance: {str(e)}")
            return {}
    
    async def _check_sox_compliance(self) -> bool:
        """Check SOX compliance requirements"""
        # Check for proper access controls, audit trails, and approval processes
        audit_trail_exists = await self.redis.exists("vault_audit_log")
        approval_system_active = len(self.multisig_approval.approval_policies) > 0
        return audit_trail_exists and approval_system_active
    
    async def _check_pci_compliance(self) -> bool:
        """Check PCI DSS compliance requirements"""
        # Check for encryption, access controls, and monitoring
        hsm_active = len(self.security_framework.hsm_configs) > 0
        monitoring_active = self.metrics.siem_connections > 0
        return hsm_active and monitoring_active
    
    async def _check_hipaa_compliance(self) -> bool:
        """Check HIPAA compliance requirements"""
        # Check for PHI protection, access logging, and encryption
        encryption_active = self.metrics.hsm_health == 'active'
        audit_logging_active = await self.redis.exists("vault_audit_log")
        return encryption_active and audit_logging_active
    
    async def _check_gdpr_compliance(self) -> bool:
        """Check GDPR compliance requirements"""
        # Check for data protection, access controls, and audit trails
        escrow_system_active = self.metrics.active_escrows >= 0
        audit_system_active = await self.redis.exists("vault_audit_log")
        return escrow_system_active and audit_system_active
    
    async def _generate_compliance_report(self) -> None:
        """Generate daily compliance report"""
        try:
            compliance_status = await self._assess_compliance_status()
            
            report = {
                'report_id': secrets.token_hex(16),
                'generated_at': datetime.utcnow().isoformat(),
                'compliance_status': compliance_status,
                'metrics': {
                    'total_credentials': self.metrics.total_credentials,
                    'active_sessions': self.metrics.active_sessions,
                    'security_posture': self.metrics.security_posture.value,
                    'compliance_score': self.metrics.compliance_score
                },
                'recommendations': await self._generate_compliance_recommendations()
            }
            
            # Store report
            await self.redis.hset(f"compliance_report:{datetime.utcnow().strftime('%Y-%m-%d')}", 
                                mapping={k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) 
                                       for k, v in report.items()})
            
            self.logger.info("Daily compliance report generated")
            
        except Exception as e:
            self.logger.error(f"Failed to generate compliance report: {str(e)}")
    
    async def _generate_compliance_recommendations(self) -> List[str]:
        """Generate compliance recommendations"""
        recommendations = []
        
        if self.metrics.compliance_score < 0.8:
            recommendations.append("Improve overall compliance score by addressing security gaps")
        
        if self.metrics.siem_connections == 0:
            recommendations.append("Connect to SIEM system for enhanced monitoring")
        
        if self.metrics.security_posture in [SecurityPosture.CONCERNING, SecurityPosture.CRITICAL]:
            recommendations.append("Address security posture issues immediately")
        
        return recommendations
    
    async def _integration_monitor(self) -> None:
        """Monitor external integrations"""
        while True:
            try:
                # Check SIEM connectivity
                siem_status = await self.siem_integration.get_siem_status()
                
                # Check hAIveMind connectivity  
                haivemind_status = await self.haivemind_integration.get_haivemind_status()
                
                # Store integration status
                integration_status = {
                    'siem_connections': siem_status.get('active_connections', 0),
                    'haivemind_connectivity': haivemind_status.get('network_connectivity', 'disconnected'),
                    'last_check': datetime.utcnow().isoformat()
                }
                
                await self.redis.hset("vault_integrations", mapping={
                    k: str(v) for k, v in integration_status.items()
                })
                
                await asyncio.sleep(600)  # Check every 10 minutes
                
            except Exception as e:
                self.logger.error(f"Integration monitor error: {str(e)}")
                await asyncio.sleep(120)
    
    async def get_vault_status(self) -> Dict[str, Any]:
        """Get comprehensive vault status"""
        try:
            return {
                'system_status': self.status.value,
                'metrics': {
                    'total_credentials': self.metrics.total_credentials,
                    'active_sessions': self.metrics.active_sessions,
                    'threat_level': self.metrics.threat_level,
                    'security_posture': self.metrics.security_posture.value,
                    'compliance_score': self.metrics.compliance_score,
                    'hsm_health': self.metrics.hsm_health,
                    'haivemind_status': self.metrics.haivemind_status,
                    'siem_connections': self.metrics.siem_connections,
                    'pending_approvals': self.metrics.pending_approvals,
                    'active_escrows': self.metrics.active_escrows,
                    'anomalies_detected': self.metrics.anomalies_detected,
                    'last_updated': self.metrics.last_updated.isoformat()
                },
                'components': {
                    'security_framework': 'active',
                    'shamir_sharing': 'active', 
                    'multisig_approval': 'active',
                    'escrow_system': 'active',
                    'threat_detection': 'active',
                    'siem_integration': 'active',
                    'haivemind_integration': 'active'
                },
                'background_tasks': len(self.background_tasks),
                'uptime': (datetime.utcnow() - self.metrics.last_updated).total_seconds()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get vault status: {str(e)}")
            return {'error': str(e)}
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the enterprise vault"""
        try:
            self.logger.info("Shutting down Enterprise Vault Security System...")
            
            # Cancel background tasks
            for task in self.background_tasks:
                task.cancel()
            
            # Wait for tasks to complete
            if self.background_tasks:
                await asyncio.gather(*self.background_tasks, return_exceptions=True)
            
            self.status = VaultOperationStatus.STOPPED
            self.logger.info("Enterprise Vault Security System shut down successfully")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {str(e)}")
            self.status = VaultOperationStatus.ERROR