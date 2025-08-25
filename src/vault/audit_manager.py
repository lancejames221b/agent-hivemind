"""
Comprehensive Audit Manager for Credential Vault
Provides detailed audit logging, access tracking, and compliance reporting.

Author: Lance James, Unit 221B
"""

import asyncio
import logging
import json
import hashlib
import secrets
import geoip2.database
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
import ipaddress
from urllib.parse import urlparse
import redis
import asyncpg
from contextlib import asynccontextmanager

from .database_manager import DatabaseManager


class AuditEventType(Enum):
    """Types of audit events"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    ROTATE = "rotate"
    ACCESS = "access"
    ADMIN = "admin"
    AUTH = "auth"
    EXPORT = "export"
    IMPORT = "import"
    EMERGENCY = "emergency"
    SHARE = "share"
    REVOKE = "revoke"
    BACKUP = "backup"
    RESTORE = "restore"


class AuditResult(Enum):
    """Audit event results"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    DENIED = "denied"
    ERROR = "error"


class RiskLevel(Enum):
    """Risk levels for audit events"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceFramework(Enum):
    """Compliance frameworks"""
    SOX = "sox"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    GDPR = "gdpr"
    SOC2 = "soc2"
    ISO27001 = "iso27001"
    NIST = "nist"


@dataclass
class AuditEvent:
    """Comprehensive audit event"""
    event_id: str
    event_type: AuditEventType
    user_id: str
    credential_id: Optional[str]
    action: str
    result: AuditResult
    timestamp: datetime
    
    # Request context
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    
    # Security context
    risk_score: float = 0.0
    anomaly_detected: bool = False
    mfa_verified: bool = False
    
    # Timing
    duration_ms: Optional[int] = None
    
    # Compliance
    compliance_flags: List[str] = field(default_factory=list)
    
    # Additional context
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Geographic info
    country: Optional[str] = None
    city: Optional[str] = None
    
    # Device fingerprint
    device_fingerprint: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'user_id': self.user_id,
            'credential_id': self.credential_id,
            'action': self.action,
            'result': self.result.value,
            'timestamp': self.timestamp.isoformat(),
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'session_id': self.session_id,
            'request_id': self.request_id,
            'risk_score': self.risk_score,
            'anomaly_detected': self.anomaly_detected,
            'mfa_verified': self.mfa_verified,
            'duration_ms': self.duration_ms,
            'compliance_flags': self.compliance_flags,
            'metadata': self.metadata,
            'country': self.country,
            'city': self.city,
            'device_fingerprint': self.device_fingerprint
        }


@dataclass
class AccessPattern:
    """User access pattern analysis"""
    user_id: str
    credential_id: str
    access_count: int
    first_access: datetime
    last_access: datetime
    avg_duration: float
    common_ip_addresses: List[str]
    common_user_agents: List[str]
    unusual_access_times: List[datetime]
    risk_indicators: List[str]


@dataclass
class ComplianceReport:
    """Compliance report data"""
    report_id: str
    framework: ComplianceFramework
    period_start: datetime
    period_end: datetime
    total_events: int
    compliant_events: int
    non_compliant_events: int
    violations: List[Dict[str, Any]]
    recommendations: List[str]
    generated_at: datetime
    generated_by: str


class AnomalyDetector:
    """Detects anomalous access patterns"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get('anomaly_detection', {})
        self.enabled = self.config.get('enabled', True)
        self.sensitivity = self.config.get('sensitivity', 0.7)
        self.learning_period_days = self.config.get('learning_period_days', 30)
        
    async def analyze_event(self, event: AuditEvent, user_history: List[AuditEvent]) -> Tuple[bool, float, List[str]]:
        """Analyze event for anomalies"""
        if not self.enabled:
            return False, 0.0, []
        
        anomaly_indicators = []
        risk_score = 0.0
        
        # Time-based anomalies
        time_risk, time_indicators = self._analyze_time_patterns(event, user_history)
        risk_score += time_risk
        anomaly_indicators.extend(time_indicators)
        
        # Location-based anomalies
        location_risk, location_indicators = self._analyze_location_patterns(event, user_history)
        risk_score += location_risk
        anomaly_indicators.extend(location_indicators)
        
        # Frequency-based anomalies
        frequency_risk, frequency_indicators = self._analyze_frequency_patterns(event, user_history)
        risk_score += frequency_risk
        anomaly_indicators.extend(frequency_indicators)
        
        # Device-based anomalies
        device_risk, device_indicators = self._analyze_device_patterns(event, user_history)
        risk_score += device_risk
        anomaly_indicators.extend(device_indicators)
        
        # Normalize risk score
        risk_score = min(1.0, risk_score)
        is_anomaly = risk_score > self.sensitivity
        
        return is_anomaly, risk_score, anomaly_indicators
    
    def _analyze_time_patterns(self, event: AuditEvent, history: List[AuditEvent]) -> Tuple[float, List[str]]:
        """Analyze time-based access patterns"""
        if not history:
            return 0.0, []
        
        indicators = []
        risk = 0.0
        
        # Get user's typical access hours
        access_hours = [h.timestamp.hour for h in history if h.result == AuditResult.SUCCESS]
        if access_hours:
            current_hour = event.timestamp.hour
            hour_counts = {}
            for hour in access_hours:
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
            
            # If current hour is rarely used, it's suspicious
            current_hour_count = hour_counts.get(current_hour, 0)
            max_hour_count = max(hour_counts.values())
            
            if current_hour_count < max_hour_count * 0.1:  # Less than 10% of peak usage
                risk += 0.3
                indicators.append(f"Unusual access time: {current_hour}:00")
        
        # Check for weekend access if user typically doesn't work weekends
        weekend_accesses = [h for h in history if h.timestamp.weekday() >= 5]
        if len(weekend_accesses) < len(history) * 0.1 and event.timestamp.weekday() >= 5:
            risk += 0.2
            indicators.append("Weekend access detected")
        
        return risk, indicators
    
    def _analyze_location_patterns(self, event: AuditEvent, history: List[AuditEvent]) -> Tuple[float, List[str]]:
        """Analyze location-based access patterns"""
        if not event.ip_address or not history:
            return 0.0, []
        
        indicators = []
        risk = 0.0
        
        # Get historical IP addresses
        historical_ips = [h.ip_address for h in history if h.ip_address and h.result == AuditResult.SUCCESS]
        
        if historical_ips and event.ip_address not in historical_ips:
            # New IP address
            risk += 0.4
            indicators.append(f"New IP address: {event.ip_address}")
            
            # Check if it's from a different country
            if event.country:
                historical_countries = [h.country for h in history if h.country]
                if historical_countries and event.country not in historical_countries:
                    risk += 0.3
                    indicators.append(f"Access from new country: {event.country}")
        
        # Check for impossible travel (accessing from different locations too quickly)
        recent_events = [h for h in history if (event.timestamp - h.timestamp).total_seconds() < 3600]  # Last hour
        if recent_events:
            for recent_event in recent_events:
                if (recent_event.country and event.country and 
                    recent_event.country != event.country and
                    (event.timestamp - recent_event.timestamp).total_seconds() < 1800):  # 30 minutes
                    risk += 0.5
                    indicators.append("Impossible travel detected")
                    break
        
        return risk, indicators
    
    def _analyze_frequency_patterns(self, event: AuditEvent, history: List[AuditEvent]) -> Tuple[float, List[str]]:
        """Analyze frequency-based access patterns"""
        if not history:
            return 0.0, []
        
        indicators = []
        risk = 0.0
        
        # Check for burst activity
        recent_events = [h for h in history if (event.timestamp - h.timestamp).total_seconds() < 300]  # Last 5 minutes
        if len(recent_events) > 10:  # More than 10 accesses in 5 minutes
            risk += 0.3
            indicators.append("Burst activity detected")
        
        # Check for unusual credential access patterns
        if event.credential_id:
            credential_history = [h for h in history if h.credential_id == event.credential_id]
            if credential_history:
                avg_daily_access = len(credential_history) / max(1, (datetime.utcnow() - min(h.timestamp for h in credential_history)).days)
                recent_access_count = len([h for h in credential_history if (event.timestamp - h.timestamp).days < 1])
                
                if recent_access_count > avg_daily_access * 3:  # 3x normal daily access
                    risk += 0.2
                    indicators.append("Unusual credential access frequency")
        
        return risk, indicators
    
    def _analyze_device_patterns(self, event: AuditEvent, history: List[AuditEvent]) -> Tuple[float, List[str]]:
        """Analyze device-based access patterns"""
        if not event.user_agent or not history:
            return 0.0, []
        
        indicators = []
        risk = 0.0
        
        # Get historical user agents
        historical_agents = [h.user_agent for h in history if h.user_agent and h.result == AuditResult.SUCCESS]
        
        if historical_agents and event.user_agent not in historical_agents:
            risk += 0.2
            indicators.append("New device/browser detected")
        
        # Check device fingerprint if available
        if event.device_fingerprint:
            historical_fingerprints = [h.device_fingerprint for h in history if h.device_fingerprint]
            if historical_fingerprints and event.device_fingerprint not in historical_fingerprints:
                risk += 0.3
                indicators.append("New device fingerprint detected")
        
        return risk, indicators


class ComplianceManager:
    """Manages compliance requirements and reporting"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get('compliance', {})
        self.enabled_frameworks = [ComplianceFramework(f) for f in self.config.get('frameworks', [])]
        self.retention_days = self.config.get('retention_days', 2555)  # 7 years default
        
    async def check_compliance(self, event: AuditEvent) -> List[str]:
        """Check event compliance against enabled frameworks"""
        violations = []
        
        for framework in self.enabled_frameworks:
            framework_violations = await self._check_framework_compliance(event, framework)
            violations.extend(framework_violations)
        
        return violations
    
    async def _check_framework_compliance(self, event: AuditEvent, framework: ComplianceFramework) -> List[str]:
        """Check compliance for specific framework"""
        violations = []
        
        if framework == ComplianceFramework.SOX:
            violations.extend(await self._check_sox_compliance(event))
        elif framework == ComplianceFramework.HIPAA:
            violations.extend(await self._check_hipaa_compliance(event))
        elif framework == ComplianceFramework.PCI_DSS:
            violations.extend(await self._check_pci_compliance(event))
        elif framework == ComplianceFramework.GDPR:
            violations.extend(await self._check_gdpr_compliance(event))
        
        return violations
    
    async def _check_sox_compliance(self, event: AuditEvent) -> List[str]:
        """Check SOX compliance requirements"""
        violations = []
        
        # SOX requires detailed audit trails for financial systems
        if not event.user_id:
            violations.append("SOX: Missing user identification")
        
        if event.event_type in [AuditEventType.DELETE, AuditEventType.UPDATE] and not event.mfa_verified:
            violations.append("SOX: Critical operations require MFA verification")
        
        return violations
    
    async def _check_hipaa_compliance(self, event: AuditEvent) -> List[str]:
        """Check HIPAA compliance requirements"""
        violations = []
        
        # HIPAA requires minimum necessary access
        if event.event_type == AuditEventType.READ and not event.metadata.get('business_justification'):
            violations.append("HIPAA: Missing business justification for access")
        
        return violations
    
    async def _check_pci_compliance(self, event: AuditEvent) -> List[str]:
        """Check PCI DSS compliance requirements"""
        violations = []
        
        # PCI requires secure authentication
        if not event.mfa_verified and event.event_type in [AuditEventType.ACCESS, AuditEventType.READ]:
            violations.append("PCI: Multi-factor authentication required")
        
        return violations
    
    async def _check_gdpr_compliance(self, event: AuditEvent) -> List[str]:
        """Check GDPR compliance requirements"""
        violations = []
        
        # GDPR requires lawful basis for processing
        if event.event_type == AuditEventType.READ and not event.metadata.get('lawful_basis'):
            violations.append("GDPR: Missing lawful basis for data processing")
        
        return violations
    
    async def generate_compliance_report(self, framework: ComplianceFramework,
                                       start_date: datetime, end_date: datetime,
                                       events: List[AuditEvent]) -> ComplianceReport:
        """Generate compliance report for framework"""
        violations = []
        compliant_count = 0
        
        for event in events:
            event_violations = await self._check_framework_compliance(event, framework)
            if event_violations:
                violations.extend([{
                    'event_id': event.event_id,
                    'violation': violation,
                    'timestamp': event.timestamp.isoformat()
                } for violation in event_violations])
            else:
                compliant_count += 1
        
        recommendations = self._generate_compliance_recommendations(framework, violations)
        
        return ComplianceReport(
            report_id=secrets.token_urlsafe(16),
            framework=framework,
            period_start=start_date,
            period_end=end_date,
            total_events=len(events),
            compliant_events=compliant_count,
            non_compliant_events=len(events) - compliant_count,
            violations=violations,
            recommendations=recommendations,
            generated_at=datetime.utcnow(),
            generated_by="audit_manager"
        )
    
    def _generate_compliance_recommendations(self, framework: ComplianceFramework, 
                                           violations: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on violations"""
        recommendations = []
        
        violation_types = [v['violation'] for v in violations]
        
        if any('MFA' in v for v in violation_types):
            recommendations.append("Implement mandatory multi-factor authentication for critical operations")
        
        if any('justification' in v for v in violation_types):
            recommendations.append("Require business justification for all data access requests")
        
        if any('identification' in v for v in violation_types):
            recommendations.append("Ensure all actions are properly attributed to authenticated users")
        
        return recommendations


class AuditManager:
    """Comprehensive audit management system"""
    
    def __init__(self, config: Dict[str, Any], redis_client: Optional[redis.Redis],
                 database_manager: DatabaseManager):
        self.config = config
        self.redis = redis_client
        self.database_manager = database_manager
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.anomaly_detector = AnomalyDetector(config)
        self.compliance_manager = ComplianceManager(config)
        
        # Audit configuration
        audit_config = config.get('vault', {}).get('audit', {})
        self.enabled = audit_config.get('enabled', True)
        self.async_logging = audit_config.get('async_logging', True)
        self.batch_size = audit_config.get('batch_size', 100)
        self.flush_interval = audit_config.get('flush_interval', 30)
        
        # GeoIP database for location detection
        self.geoip_db_path = audit_config.get('geoip_db_path')
        self.geoip_reader = None
        if self.geoip_db_path:
            try:
                self.geoip_reader = geoip2.database.Reader(self.geoip_db_path)
            except Exception as e:
                self.logger.warning(f"Failed to load GeoIP database: {str(e)}")
        
        # Event queue for async processing
        self.event_queue = asyncio.Queue(maxsize=1000)
        self.processing_events = False
        
    async def initialize(self) -> bool:
        """Initialize audit manager"""
        try:
            if self.async_logging:
                # Start background event processor
                asyncio.create_task(self._process_audit_events())
                self.processing_events = True
            
            self.logger.info("Audit manager initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize audit manager: {str(e)}")
            return False
    
    async def shutdown(self):
        """Shutdown audit manager"""
        self.processing_events = False
        
        # Process remaining events
        while not self.event_queue.empty():
            try:
                event = self.event_queue.get_nowait()
                await self._store_audit_event(event)
            except asyncio.QueueEmpty:
                break
        
        if self.geoip_reader:
            self.geoip_reader.close()
        
        self.logger.info("Audit manager shutdown")
    
    async def log_event(self, event_type: AuditEventType, user_id: str, action: str,
                       result: AuditResult, credential_id: Optional[str] = None,
                       ip_address: Optional[str] = None, user_agent: Optional[str] = None,
                       session_id: Optional[str] = None, request_id: Optional[str] = None,
                       duration_ms: Optional[int] = None, mfa_verified: bool = False,
                       metadata: Dict[str, Any] = None) -> str:
        """Log audit event"""
        try:
            # Create audit event
            event = AuditEvent(
                event_id=secrets.token_urlsafe(16),
                event_type=event_type,
                user_id=user_id,
                credential_id=credential_id,
                action=action,
                result=result,
                timestamp=datetime.utcnow(),
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id,
                request_id=request_id,
                duration_ms=duration_ms,
                mfa_verified=mfa_verified,
                metadata=metadata or {}
            )
            
            # Enrich event with additional data
            await self._enrich_event(event)
            
            # Analyze for anomalies
            await self._analyze_event_anomalies(event)
            
            # Check compliance
            compliance_violations = await self.compliance_manager.check_compliance(event)
            if compliance_violations:
                event.compliance_flags = compliance_violations
            
            # Store event
            if self.async_logging:
                await self.event_queue.put(event)
            else:
                await self._store_audit_event(event)
            
            return event.event_id
            
        except Exception as e:
            self.logger.error(f"Failed to log audit event: {str(e)}")
            return ""
    
    async def _enrich_event(self, event: AuditEvent) -> None:
        """Enrich event with additional context"""
        try:
            # Add geographic information
            if event.ip_address and self.geoip_reader:
                try:
                    response = self.geoip_reader.city(event.ip_address)
                    event.country = response.country.name
                    event.city = response.city.name
                except Exception:
                    pass
            
            # Generate device fingerprint
            if event.user_agent:
                event.device_fingerprint = hashlib.sha256(
                    f"{event.user_agent}:{event.ip_address}".encode()
                ).hexdigest()[:16]
            
            # Add risk assessment
            event.risk_score = await self._calculate_base_risk_score(event)
            
        except Exception as e:
            self.logger.error(f"Failed to enrich event: {str(e)}")
    
    async def _analyze_event_anomalies(self, event: AuditEvent) -> None:
        """Analyze event for anomalies"""
        try:
            # Get user's recent history
            user_history = await self._get_user_audit_history(event.user_id, days=30)
            
            # Analyze for anomalies
            is_anomaly, risk_score, indicators = await self.anomaly_detector.analyze_event(
                event, user_history
            )
            
            if is_anomaly:
                event.anomaly_detected = True
                event.risk_score = max(event.risk_score, risk_score)
                event.metadata['anomaly_indicators'] = indicators
                
                # Log high-risk anomalies
                if risk_score > 0.8:
                    self.logger.warning(f"High-risk anomaly detected: {event.event_id} - {indicators}")
            
        except Exception as e:
            self.logger.error(f"Failed to analyze event anomalies: {str(e)}")
    
    async def _calculate_base_risk_score(self, event: AuditEvent) -> float:
        """Calculate base risk score for event"""
        risk_score = 0.0
        
        # Event type risk
        high_risk_events = [AuditEventType.DELETE, AuditEventType.EMERGENCY, AuditEventType.EXPORT]
        medium_risk_events = [AuditEventType.UPDATE, AuditEventType.ROTATE, AuditEventType.SHARE]
        
        if event.event_type in high_risk_events:
            risk_score += 0.4
        elif event.event_type in medium_risk_events:
            risk_score += 0.2
        
        # Result risk
        if event.result in [AuditResult.FAILURE, AuditResult.DENIED]:
            risk_score += 0.3
        
        # MFA risk
        if not event.mfa_verified and event.event_type in high_risk_events:
            risk_score += 0.2
        
        # Time-based risk (outside business hours)
        hour = event.timestamp.hour
        if hour < 6 or hour > 22:  # Outside 6 AM - 10 PM
            risk_score += 0.1
        
        return min(1.0, risk_score)
    
    async def _get_user_audit_history(self, user_id: str, days: int = 30) -> List[AuditEvent]:
        """Get user's audit history"""
        try:
            # This would query the database for user's recent audit events
            # Placeholder implementation
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to get user audit history: {str(e)}")
            return []
    
    async def _process_audit_events(self):
        """Background task to process audit events"""
        batch = []
        last_flush = datetime.utcnow()
        
        while self.processing_events:
            try:
                # Collect events for batch processing
                try:
                    event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
                    batch.append(event)
                except asyncio.TimeoutError:
                    pass
                
                # Flush batch if size limit reached or time limit exceeded
                should_flush = (
                    len(batch) >= self.batch_size or
                    (batch and (datetime.utcnow() - last_flush).total_seconds() > self.flush_interval)
                )
                
                if should_flush:
                    await self._store_audit_events_batch(batch)
                    batch.clear()
                    last_flush = datetime.utcnow()
                
            except Exception as e:
                self.logger.error(f"Audit event processing error: {str(e)}")
                await asyncio.sleep(1)
        
        # Flush remaining events
        if batch:
            await self._store_audit_events_batch(batch)
    
    async def _store_audit_event(self, event: AuditEvent) -> bool:
        """Store single audit event"""
        try:
            return await self.database_manager.store_audit_log(
                user_id=event.user_id,
                credential_id=event.credential_id,
                event_type=event.event_type.value,
                action=event.action,
                result=event.result.value,
                ip_address=event.ip_address,
                user_agent=event.user_agent,
                metadata=event.to_dict(),
                risk_score=event.risk_score
            )
            
        except Exception as e:
            self.logger.error(f"Failed to store audit event: {str(e)}")
            return False
    
    async def _store_audit_events_batch(self, events: List[AuditEvent]) -> bool:
        """Store batch of audit events"""
        try:
            # Use database transaction for batch insert
            async with self.database_manager.get_transaction() as conn:
                for event in events:
                    await self.database_manager.store_audit_log(
                        user_id=event.user_id,
                        credential_id=event.credential_id,
                        event_type=event.event_type.value,
                        action=event.action,
                        result=event.result.value,
                        ip_address=event.ip_address,
                        user_agent=event.user_agent,
                        metadata=event.to_dict(),
                        risk_score=event.risk_score,
                        connection=conn
                    )
            
            self.logger.debug(f"Stored batch of {len(events)} audit events")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store audit events batch: {str(e)}")
            return False
    
    async def get_audit_trail(self, credential_id: str, days: int = 30) -> List[AuditEvent]:
        """Get audit trail for credential"""
        try:
            # This would query the database for credential audit events
            # Placeholder implementation
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to get audit trail: {str(e)}")
            return []
    
    async def get_user_activity(self, user_id: str, days: int = 30) -> List[AuditEvent]:
        """Get user activity"""
        try:
            # This would query the database for user audit events
            # Placeholder implementation
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to get user activity: {str(e)}")
            return []
    
    async def analyze_access_patterns(self, user_id: str, credential_id: str) -> AccessPattern:
        """Analyze user access patterns for credential"""
        try:
            # Get audit history
            events = await self._get_credential_audit_history(user_id, credential_id)
            
            if not events:
                return AccessPattern(
                    user_id=user_id,
                    credential_id=credential_id,
                    access_count=0,
                    first_access=datetime.utcnow(),
                    last_access=datetime.utcnow(),
                    avg_duration=0.0,
                    common_ip_addresses=[],
                    common_user_agents=[],
                    unusual_access_times=[],
                    risk_indicators=[]
                )
            
            # Analyze patterns
            access_count = len(events)
            first_access = min(e.timestamp for e in events)
            last_access = max(e.timestamp for e in events)
            
            # Calculate average duration
            durations = [e.duration_ms for e in events if e.duration_ms]
            avg_duration = sum(durations) / len(durations) if durations else 0.0
            
            # Find common IP addresses
            ip_counts = {}
            for event in events:
                if event.ip_address:
                    ip_counts[event.ip_address] = ip_counts.get(event.ip_address, 0) + 1
            common_ips = sorted(ip_counts.keys(), key=lambda x: ip_counts[x], reverse=True)[:5]
            
            # Find common user agents
            ua_counts = {}
            for event in events:
                if event.user_agent:
                    ua_counts[event.user_agent] = ua_counts.get(event.user_agent, 0) + 1
            common_uas = sorted(ua_counts.keys(), key=lambda x: ua_counts[x], reverse=True)[:3]
            
            # Find unusual access times
            unusual_times = [e.timestamp for e in events if e.anomaly_detected]
            
            # Identify risk indicators
            risk_indicators = []
            if len(set(e.ip_address for e in events if e.ip_address)) > 10:
                risk_indicators.append("Multiple IP addresses used")
            
            if any(e.risk_score > 0.7 for e in events):
                risk_indicators.append("High-risk access detected")
            
            return AccessPattern(
                user_id=user_id,
                credential_id=credential_id,
                access_count=access_count,
                first_access=first_access,
                last_access=last_access,
                avg_duration=avg_duration,
                common_ip_addresses=common_ips,
                common_user_agents=common_uas,
                unusual_access_times=unusual_times,
                risk_indicators=risk_indicators
            )
            
        except Exception as e:
            self.logger.error(f"Failed to analyze access patterns: {str(e)}")
            return AccessPattern(
                user_id=user_id,
                credential_id=credential_id,
                access_count=0,
                first_access=datetime.utcnow(),
                last_access=datetime.utcnow(),
                avg_duration=0.0,
                common_ip_addresses=[],
                common_user_agents=[],
                unusual_access_times=[],
                risk_indicators=["Analysis failed"]
            )
    
    async def _get_credential_audit_history(self, user_id: str, credential_id: str) -> List[AuditEvent]:
        """Get audit history for specific credential and user"""
        try:
            # This would query the database
            # Placeholder implementation
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to get credential audit history: {str(e)}")
            return []
    
    async def generate_compliance_report(self, framework: ComplianceFramework,
                                       start_date: datetime, end_date: datetime) -> ComplianceReport:
        """Generate compliance report"""
        try:
            # Get audit events for period
            events = []  # Would query database for events in date range
            
            return await self.compliance_manager.generate_compliance_report(
                framework, start_date, end_date, events
            )
            
        except Exception as e:
            self.logger.error(f"Failed to generate compliance report: {str(e)}")
            return ComplianceReport(
                report_id="error",
                framework=framework,
                period_start=start_date,
                period_end=end_date,
                total_events=0,
                compliant_events=0,
                non_compliant_events=0,
                violations=[],
                recommendations=[f"Report generation failed: {str(e)}"],
                generated_at=datetime.utcnow(),
                generated_by="audit_manager"
            )
    
    async def get_audit_statistics(self) -> Dict[str, Any]:
        """Get comprehensive audit statistics"""
        try:
            # This would query the database for various statistics
            return {
                'total_events': 0,
                'events_by_type': {},
                'events_by_result': {},
                'high_risk_events': 0,
                'anomalies_detected': 0,
                'compliance_violations': 0,
                'unique_users': 0,
                'unique_credentials': 0,
                'avg_risk_score': 0.0,
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get audit statistics: {str(e)}")
            return {'error': str(e)}