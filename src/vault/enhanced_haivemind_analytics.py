"""
Enhanced hAIveMind Security Analytics and Awareness
Advanced security analytics, pattern recognition, and collaborative intelligence.

Author: Lance James, Unit 221B
"""

import asyncio
import logging
import json
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Set
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import secrets
import hashlib
import statistics
from collections import defaultdict, deque
import redis
from ..memory_server import MemoryMCPServer


class AnalyticsType(Enum):
    """Types of security analytics"""
    BEHAVIORAL_ANALYSIS = "behavioral_analysis"
    PATTERN_RECOGNITION = "pattern_recognition"
    ANOMALY_DETECTION = "anomaly_detection"
    RISK_ASSESSMENT = "risk_assessment"
    THREAT_HUNTING = "threat_hunting"
    PREDICTIVE_ANALYSIS = "predictive_analysis"
    CORRELATION_ANALYSIS = "correlation_analysis"
    TREND_ANALYSIS = "trend_analysis"


class RiskLevel(Enum):
    """Risk levels for analytics"""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"
    CRITICAL = "critical"


@dataclass
class SecurityPattern:
    """Security pattern detected by analytics"""
    pattern_id: str
    pattern_type: str
    name: str
    description: str
    indicators: List[Dict[str, Any]]
    confidence_score: float
    risk_level: RiskLevel
    frequency: int
    first_seen: datetime
    last_seen: datetime
    affected_resources: List[str]
    mitre_techniques: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BehavioralBaseline:
    """User/system behavioral baseline"""
    entity_id: str
    entity_type: str  # user, service, system
    baseline_metrics: Dict[str, Any]
    confidence_level: float
    created_at: datetime
    updated_at: datetime
    sample_size: int
    validity_period: timedelta


@dataclass
class AnomalyDetection:
    """Anomaly detection result"""
    anomaly_id: str
    entity_id: str
    entity_type: str
    anomaly_type: str
    description: str
    severity: str
    confidence_score: float
    baseline_deviation: float
    detected_at: datetime
    context: Dict[str, Any]
    recommendations: List[str] = field(default_factory=list)


@dataclass
class SecurityInsight:
    """Enhanced security insight with analytics"""
    insight_id: str
    title: str
    description: str
    insight_type: AnalyticsType
    confidence_score: float
    risk_score: float
    impact_assessment: Dict[str, Any]
    evidence: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    affected_entities: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None
    validated: bool = False
    false_positive: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class AdvancedSecurityAnalytics:
    """Advanced security analytics engine"""
    
    def __init__(self, redis_client: redis.Redis, memory_server: MemoryMCPServer):
        self.redis = redis_client
        self.memory_server = memory_server
        self.logger = logging.getLogger(__name__)
        
        # Analytics state
        self.behavioral_baselines: Dict[str, BehavioralBaseline] = {}
        self.detected_patterns: Dict[str, SecurityPattern] = {}
        self.anomalies: Dict[str, AnomalyDetection] = {}
        self.security_insights: Dict[str, SecurityInsight] = {}
        
        # Analytics configuration
        self.anomaly_threshold = 2.5  # Standard deviations
        self.pattern_confidence_threshold = 0.7
        self.baseline_update_interval = timedelta(hours=24)
        self.insight_retention_days = 90
        
        # Event buffers for real-time analysis
        self.event_buffer = deque(maxlen=10000)
        self.access_patterns = defaultdict(list)
        self.user_behaviors = defaultdict(lambda: defaultdict(list))
    
    async def initialize_analytics(self) -> bool:
        """Initialize analytics engine"""
        try:
            await self._load_existing_baselines()
            await self._load_existing_patterns()
            await self._initialize_ml_models()
            
            # Start background analytics tasks
            asyncio.create_task(self._continuous_pattern_analysis())
            asyncio.create_task(self._behavioral_analysis())
            asyncio.create_task(self._anomaly_detection_loop())
            asyncio.create_task(self._insight_generation())
            asyncio.create_task(self._baseline_maintenance())
            
            self.logger.info("Advanced security analytics initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize analytics: {str(e)}")
            return False
    
    async def process_security_event(self, event: Dict[str, Any]) -> List[SecurityInsight]:
        """Process a security event and generate insights"""
        insights = []
        
        try:
            # Add event to buffer
            self.event_buffer.append({
                **event,
                'processed_at': datetime.utcnow()
            })
            
            # Update access patterns
            if event.get('event_type') == 'credential_access':
                await self._update_access_patterns(event)
            
            # Update user behavior tracking
            if event.get('user_id'):
                await self._update_user_behavior(event)
            
            # Real-time anomaly detection
            anomalies = await self._detect_real_time_anomalies(event)
            for anomaly in anomalies:
                insight = await self._create_insight_from_anomaly(anomaly)
                if insight:
                    insights.append(insight)
            
            # Pattern matching
            patterns = await self._match_security_patterns(event)
            for pattern in patterns:
                insight = await self._create_insight_from_pattern(pattern, event)
                if insight:
                    insights.append(insight)
            
            # Risk assessment
            risk_insight = await self._assess_event_risk(event)
            if risk_insight:
                insights.append(risk_insight)
            
            # Store insights in hAIveMind
            for insight in insights:
                await self._store_security_insight(insight)
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error processing security event: {str(e)}")
            return []
    
    async def _update_access_patterns(self, event: Dict[str, Any]):
        """Update credential access patterns"""
        try:
            credential_id = event.get('credential_id')
            user_id = event.get('user_id')
            timestamp = event.get('timestamp', datetime.utcnow())
            
            if credential_id and user_id:
                pattern_key = f"access_pattern:{credential_id}"
                
                access_info = {
                    'user_id': user_id,
                    'timestamp': timestamp.isoformat(),
                    'ip_address': event.get('ip_address'),
                    'user_agent': event.get('user_agent'),
                    'result': event.get('result')
                }
                
                self.access_patterns[pattern_key].append(access_info)
                
                # Keep only recent access patterns (last 30 days)
                cutoff_time = datetime.utcnow() - timedelta(days=30)
                self.access_patterns[pattern_key] = [
                    access for access in self.access_patterns[pattern_key]
                    if datetime.fromisoformat(access['timestamp']) > cutoff_time
                ]
                
        except Exception as e:
            self.logger.error(f"Error updating access patterns: {str(e)}")
    
    async def _update_user_behavior(self, event: Dict[str, Any]):
        """Update user behavioral patterns"""
        try:
            user_id = event.get('user_id')
            if not user_id:
                return
            
            timestamp = event.get('timestamp', datetime.utcnow())
            hour = timestamp.hour
            day_of_week = timestamp.weekday()
            
            behavior_data = {
                'timestamp': timestamp.isoformat(),
                'event_type': event.get('event_type'),
                'action': event.get('action'),
                'hour': hour,
                'day_of_week': day_of_week,
                'ip_address': event.get('ip_address'),
                'result': event.get('result')
            }
            
            # Track different behavioral aspects
            self.user_behaviors[user_id]['access_times'].append(hour)
            self.user_behaviors[user_id]['access_days'].append(day_of_week)
            self.user_behaviors[user_id]['ip_addresses'].append(event.get('ip_address'))
            self.user_behaviors[user_id]['actions'].append(event.get('action'))
            self.user_behaviors[user_id]['events'].append(behavior_data)
            
            # Maintain sliding window (last 90 days)
            cutoff_time = datetime.utcnow() - timedelta(days=90)
            for behavior_type in self.user_behaviors[user_id]:
                if behavior_type == 'events':
                    self.user_behaviors[user_id][behavior_type] = [
                        event for event in self.user_behaviors[user_id][behavior_type]
                        if datetime.fromisoformat(event['timestamp']) > cutoff_time
                    ]
                else:
                    # Keep last 1000 entries for other behavior types
                    if len(self.user_behaviors[user_id][behavior_type]) > 1000:
                        self.user_behaviors[user_id][behavior_type] = \
                            self.user_behaviors[user_id][behavior_type][-1000:]
            
        except Exception as e:
            self.logger.error(f"Error updating user behavior: {str(e)}")
    
    async def _detect_real_time_anomalies(self, event: Dict[str, Any]) -> List[AnomalyDetection]:
        """Detect anomalies in real-time"""
        anomalies = []
        
        try:
            user_id = event.get('user_id')
            if not user_id:
                return anomalies
            
            # Check for unusual access times
            timestamp = event.get('timestamp', datetime.utcnow())
            hour = timestamp.hour
            
            if user_id in self.user_behaviors:
                user_behavior = self.user_behaviors[user_id]
                
                # Analyze access time patterns
                if len(user_behavior['access_times']) > 20:  # Need sufficient data
                    access_times = user_behavior['access_times']
                    mean_hour = statistics.mean(access_times)
                    std_hour = statistics.stdev(access_times) if len(access_times) > 1 else 1
                    
                    # Check if current access time is anomalous
                    if std_hour > 0:
                        z_score = abs(hour - mean_hour) / std_hour
                        if z_score > self.anomaly_threshold:
                            anomaly = AnomalyDetection(
                                anomaly_id=secrets.token_hex(8),
                                entity_id=user_id,
                                entity_type='user',
                                anomaly_type='unusual_access_time',
                                description=f'User accessed system at unusual time: {hour}:00 (normal: {mean_hour:.1f}±{std_hour:.1f})',
                                severity='medium',
                                confidence_score=min(z_score / 5.0, 1.0),
                                baseline_deviation=z_score,
                                detected_at=timestamp,
                                context={
                                    'access_hour': hour,
                                    'normal_mean': mean_hour,
                                    'normal_std': std_hour,
                                    'z_score': z_score
                                },
                                recommendations=[
                                    'Verify user identity through additional authentication',
                                    'Monitor subsequent activities closely',
                                    'Check for concurrent sessions from different locations'
                                ]
                            )
                            anomalies.append(anomaly)
                
                # Check for unusual IP addresses
                ip_address = event.get('ip_address')
                if ip_address and len(user_behavior['ip_addresses']) > 10:
                    recent_ips = set(user_behavior['ip_addresses'][-50:])  # Last 50 IPs
                    if ip_address not in recent_ips:
                        # New IP address
                        anomaly = AnomalyDetection(
                            anomaly_id=secrets.token_hex(8),
                            entity_id=user_id,
                            entity_type='user',
                            anomaly_type='new_ip_address',
                            description=f'User accessed from new IP address: {ip_address}',
                            severity='medium',
                            confidence_score=0.8,
                            baseline_deviation=1.0,
                            detected_at=timestamp,
                            context={
                                'new_ip': ip_address,
                                'known_ips': list(recent_ips)[-10:]  # Last 10 known IPs
                            },
                            recommendations=[
                                'Verify user location and device',
                                'Check for VPN or proxy usage',
                                'Monitor for account takeover indicators'
                            ]
                        )
                        anomalies.append(anomaly)
                
                # Check for rapid successive access attempts
                if event.get('event_type') == 'credential_access':
                    recent_events = [
                        e for e in user_behavior.get('events', [])
                        if datetime.fromisoformat(e['timestamp']) > timestamp - timedelta(minutes=5)
                        and e.get('event_type') == 'credential_access'
                    ]
                    
                    if len(recent_events) > 10:  # More than 10 accesses in 5 minutes
                        anomaly = AnomalyDetection(
                            anomaly_id=secrets.token_hex(8),
                            entity_id=user_id,
                            entity_type='user',
                            anomaly_type='rapid_access_pattern',
                            description=f'User made {len(recent_events)} credential accesses in 5 minutes',
                            severity='high',
                            confidence_score=0.9,
                            baseline_deviation=len(recent_events) / 2.0,
                            detected_at=timestamp,
                            context={
                                'access_count': len(recent_events),
                                'time_window': '5 minutes'
                            },
                            recommendations=[
                                'Investigate potential automated access',
                                'Check for compromised credentials',
                                'Consider temporary access restrictions'
                            ]
                        )
                        anomalies.append(anomaly)
            
            return anomalies
            
        except Exception as e:
            self.logger.error(f"Error detecting real-time anomalies: {str(e)}")
            return []
    
    async def _match_security_patterns(self, event: Dict[str, Any]) -> List[SecurityPattern]:
        """Match event against known security patterns"""
        matched_patterns = []
        
        try:
            # Pattern: Failed login followed by successful access
            if event.get('event_type') == 'credential_access' and event.get('result') == 'success':
                user_id = event.get('user_id')
                if user_id and user_id in self.user_behaviors:
                    recent_events = [
                        e for e in self.user_behaviors[user_id].get('events', [])
                        if datetime.fromisoformat(e['timestamp']) > datetime.utcnow() - timedelta(minutes=30)
                    ]
                    
                    failed_attempts = [e for e in recent_events if e.get('result') == 'failure']
                    if len(failed_attempts) >= 3:  # 3+ failed attempts before success
                        pattern = SecurityPattern(
                            pattern_id=f"failed_then_success_{secrets.token_hex(4)}",
                            pattern_type="authentication_pattern",
                            name="Failed Login Then Success",
                            description="Multiple failed login attempts followed by successful access",
                            indicators=[
                                {'type': 'failed_attempts', 'count': len(failed_attempts)},
                                {'type': 'success_after_failures', 'user_id': user_id}
                            ],
                            confidence_score=0.8,
                            risk_level=RiskLevel.HIGH,
                            frequency=1,
                            first_seen=datetime.utcnow(),
                            last_seen=datetime.utcnow(),
                            affected_resources=[user_id],
                            mitre_techniques=['T1110'],  # Brute Force
                            metadata={
                                'failed_attempts': len(failed_attempts),
                                'time_window': '30 minutes'
                            }
                        )
                        matched_patterns.append(pattern)
            
            # Pattern: Off-hours administrative activity
            if (event.get('event_type') in ['admin', 'create', 'delete'] and 
                event.get('timestamp', datetime.utcnow()).hour in range(0, 6)):
                
                pattern = SecurityPattern(
                    pattern_id=f"off_hours_admin_{secrets.token_hex(4)}",
                    pattern_type="temporal_pattern",
                    name="Off-Hours Administrative Activity",
                    description="Administrative actions performed during off-hours",
                    indicators=[
                        {'type': 'off_hours_activity', 'hour': event.get('timestamp', datetime.utcnow()).hour},
                        {'type': 'admin_action', 'action': event.get('action')}
                    ],
                    confidence_score=0.7,
                    risk_level=RiskLevel.MEDIUM,
                    frequency=1,
                    first_seen=datetime.utcnow(),
                    last_seen=datetime.utcnow(),
                    affected_resources=[event.get('user_id', 'unknown')],
                    mitre_techniques=['T1078'],  # Valid Accounts
                    metadata={
                        'access_hour': event.get('timestamp', datetime.utcnow()).hour,
                        'action_type': event.get('action')
                    }
                )
                matched_patterns.append(pattern)
            
            # Pattern: Privilege escalation sequence
            if event.get('event_type') == 'permission_grant':
                user_id = event.get('user_id')
                if user_id and user_id in self.user_behaviors:
                    recent_events = [
                        e for e in self.user_behaviors[user_id].get('events', [])
                        if datetime.fromisoformat(e['timestamp']) > datetime.utcnow() - timedelta(hours=1)
                        and e.get('event_type') in ['permission_grant', 'role_assignment']
                    ]
                    
                    if len(recent_events) >= 2:  # Multiple privilege changes
                        pattern = SecurityPattern(
                            pattern_id=f"privilege_escalation_{secrets.token_hex(4)}",
                            pattern_type="privilege_pattern",
                            name="Rapid Privilege Escalation",
                            description="Multiple privilege changes in short time period",
                            indicators=[
                                {'type': 'privilege_changes', 'count': len(recent_events)},
                                {'type': 'time_window', 'duration': '1 hour'}
                            ],
                            confidence_score=0.85,
                            risk_level=RiskLevel.HIGH,
                            frequency=1,
                            first_seen=datetime.utcnow(),
                            last_seen=datetime.utcnow(),
                            affected_resources=[user_id],
                            mitre_techniques=['T1548'],  # Abuse Elevation Control Mechanism
                            metadata={
                                'privilege_changes': len(recent_events),
                                'time_window': '1 hour'
                            }
                        )
                        matched_patterns.append(pattern)
            
            return matched_patterns
            
        except Exception as e:
            self.logger.error(f"Error matching security patterns: {str(e)}")
            return []
    
    async def _assess_event_risk(self, event: Dict[str, Any]) -> Optional[SecurityInsight]:
        """Assess risk level of an event"""
        try:
            risk_factors = []
            risk_score = 0.0
            
            # Base risk by event type
            event_type_risks = {
                'credential_access': 0.3,
                'credential_create': 0.4,
                'credential_update': 0.5,
                'credential_delete': 0.7,
                'admin': 0.8,
                'emergency_access': 0.9
            }
            
            base_risk = event_type_risks.get(event.get('event_type'), 0.2)
            risk_score += base_risk
            risk_factors.append(f"Base risk for {event.get('event_type')}: {base_risk}")
            
            # Time-based risk
            timestamp = event.get('timestamp', datetime.utcnow())
            hour = timestamp.hour
            if hour < 6 or hour > 22:  # Off hours
                risk_score += 0.2
                risk_factors.append("Off-hours access (+0.2)")
            
            # Weekend access
            if timestamp.weekday() >= 5:  # Saturday or Sunday
                risk_score += 0.1
                risk_factors.append("Weekend access (+0.1)")
            
            # Failed result
            if event.get('result') == 'failure':
                risk_score += 0.3
                risk_factors.append("Failed operation (+0.3)")
            
            # High-risk credential types
            if event.get('credential_type') in ['admin', 'root', 'service_account']:
                risk_score += 0.2
                risk_factors.append("High-privilege credential (+0.2)")
            
            # New IP address (if we have history)
            user_id = event.get('user_id')
            ip_address = event.get('ip_address')
            if user_id and ip_address and user_id in self.user_behaviors:
                recent_ips = set(self.user_behaviors[user_id].get('ip_addresses', [])[-50:])
                if ip_address not in recent_ips:
                    risk_score += 0.3
                    risk_factors.append("New IP address (+0.3)")
            
            # Normalize risk score
            risk_score = min(risk_score, 1.0)
            
            # Only create insight for medium+ risk events
            if risk_score >= 0.5:
                risk_level = RiskLevel.CRITICAL if risk_score >= 0.9 else \
                           RiskLevel.HIGH if risk_score >= 0.7 else \
                           RiskLevel.MEDIUM
                
                insight = SecurityInsight(
                    insight_id=f"risk_assessment_{secrets.token_hex(8)}",
                    title=f"Elevated Risk Event: {event.get('action', 'Unknown Action')}",
                    description=f"Event assessed with {risk_level.value} risk level (score: {risk_score:.2f})",
                    insight_type=AnalyticsType.RISK_ASSESSMENT,
                    confidence_score=0.8,
                    risk_score=risk_score,
                    impact_assessment={
                        'risk_level': risk_level.value,
                        'risk_factors': risk_factors,
                        'potential_impact': self._assess_potential_impact(event, risk_score)
                    },
                    evidence=[{
                        'type': 'security_event',
                        'event_data': event,
                        'risk_factors': risk_factors
                    }],
                    recommendations=self._generate_risk_recommendations(risk_score, risk_factors),
                    affected_entities=[user_id] if user_id else [],
                    created_at=datetime.utcnow(),
                    metadata={
                        'risk_calculation': {
                            'base_risk': base_risk,
                            'total_risk': risk_score,
                            'factors': risk_factors
                        }
                    }
                )
                
                return insight
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error assessing event risk: {str(e)}")
            return None
    
    def _assess_potential_impact(self, event: Dict[str, Any], risk_score: float) -> Dict[str, Any]:
        """Assess potential impact of a risky event"""
        impact = {
            'confidentiality': 'low',
            'integrity': 'low',
            'availability': 'low',
            'business_impact': 'low'
        }
        
        event_type = event.get('event_type')
        
        if event_type == 'credential_access':
            impact['confidentiality'] = 'high' if risk_score > 0.7 else 'medium'
        elif event_type in ['credential_create', 'credential_update']:
            impact['integrity'] = 'high' if risk_score > 0.7 else 'medium'
        elif event_type == 'credential_delete':
            impact['availability'] = 'high'
            impact['business_impact'] = 'high' if risk_score > 0.7 else 'medium'
        elif event_type == 'admin':
            impact['confidentiality'] = 'high'
            impact['integrity'] = 'high'
            impact['availability'] = 'medium'
        
        return impact
    
    def _generate_risk_recommendations(self, risk_score: float, risk_factors: List[str]) -> List[Dict[str, Any]]:
        """Generate recommendations based on risk assessment"""
        recommendations = []
        
        if risk_score >= 0.9:
            recommendations.extend([
                {
                    'priority': 'critical',
                    'action': 'immediate_investigation',
                    'description': 'Immediately investigate this high-risk event'
                },
                {
                    'priority': 'high',
                    'action': 'user_verification',
                    'description': 'Verify user identity through out-of-band communication'
                }
            ])
        
        if risk_score >= 0.7:
            recommendations.extend([
                {
                    'priority': 'high',
                    'action': 'enhanced_monitoring',
                    'description': 'Enable enhanced monitoring for this user/resource'
                },
                {
                    'priority': 'medium',
                    'action': 'access_review',
                    'description': 'Review user access permissions and recent activities'
                }
            ])
        
        if any('New IP address' in factor for factor in risk_factors):
            recommendations.append({
                'priority': 'medium',
                'action': 'ip_verification',
                'description': 'Verify the legitimacy of the new IP address'
            })
        
        if any('Off-hours' in factor for factor in risk_factors):
            recommendations.append({
                'priority': 'medium',
                'action': 'schedule_verification',
                'description': 'Verify if off-hours access was planned or authorized'
            })
        
        return recommendations
    
    async def _create_insight_from_anomaly(self, anomaly: AnomalyDetection) -> Optional[SecurityInsight]:
        """Create security insight from anomaly detection"""
        try:
            insight = SecurityInsight(
                insight_id=f"anomaly_insight_{anomaly.anomaly_id}",
                title=f"Anomaly Detected: {anomaly.anomaly_type.replace('_', ' ').title()}",
                description=anomaly.description,
                insight_type=AnalyticsType.ANOMALY_DETECTION,
                confidence_score=anomaly.confidence_score,
                risk_score=min(anomaly.baseline_deviation / 5.0, 1.0),
                impact_assessment={
                    'anomaly_type': anomaly.anomaly_type,
                    'severity': anomaly.severity,
                    'baseline_deviation': anomaly.baseline_deviation
                },
                evidence=[{
                    'type': 'anomaly_detection',
                    'anomaly_data': {
                        'anomaly_id': anomaly.anomaly_id,
                        'entity_id': anomaly.entity_id,
                        'entity_type': anomaly.entity_type,
                        'context': anomaly.context
                    }
                }],
                recommendations=[
                    {'priority': 'medium', 'action': rec, 'description': rec}
                    for rec in anomaly.recommendations
                ],
                affected_entities=[anomaly.entity_id],
                created_at=anomaly.detected_at,
                metadata={
                    'anomaly_details': {
                        'type': anomaly.anomaly_type,
                        'confidence': anomaly.confidence_score,
                        'deviation': anomaly.baseline_deviation
                    }
                }
            )
            
            return insight
            
        except Exception as e:
            self.logger.error(f"Error creating insight from anomaly: {str(e)}")
            return None
    
    async def _create_insight_from_pattern(self, pattern: SecurityPattern, event: Dict[str, Any]) -> Optional[SecurityInsight]:
        """Create security insight from pattern match"""
        try:
            insight = SecurityInsight(
                insight_id=f"pattern_insight_{pattern.pattern_id}",
                title=f"Security Pattern Detected: {pattern.name}",
                description=pattern.description,
                insight_type=AnalyticsType.PATTERN_RECOGNITION,
                confidence_score=pattern.confidence_score,
                risk_score=self._pattern_risk_score(pattern.risk_level),
                impact_assessment={
                    'pattern_type': pattern.pattern_type,
                    'risk_level': pattern.risk_level.value,
                    'mitre_techniques': pattern.mitre_techniques
                },
                evidence=[{
                    'type': 'pattern_match',
                    'pattern_data': {
                        'pattern_id': pattern.pattern_id,
                        'pattern_type': pattern.pattern_type,
                        'indicators': pattern.indicators,
                        'triggering_event': event
                    }
                }],
                recommendations=self._generate_pattern_recommendations(pattern),
                affected_entities=pattern.affected_resources,
                created_at=datetime.utcnow(),
                metadata={
                    'pattern_details': {
                        'name': pattern.name,
                        'type': pattern.pattern_type,
                        'confidence': pattern.confidence_score,
                        'mitre_techniques': pattern.mitre_techniques
                    }
                }
            )
            
            return insight
            
        except Exception as e:
            self.logger.error(f"Error creating insight from pattern: {str(e)}")
            return None
    
    def _pattern_risk_score(self, risk_level: RiskLevel) -> float:
        """Convert risk level to numeric score"""
        risk_scores = {
            RiskLevel.VERY_LOW: 0.1,
            RiskLevel.LOW: 0.3,
            RiskLevel.MEDIUM: 0.5,
            RiskLevel.HIGH: 0.7,
            RiskLevel.VERY_HIGH: 0.9,
            RiskLevel.CRITICAL: 1.0
        }
        return risk_scores.get(risk_level, 0.5)
    
    def _generate_pattern_recommendations(self, pattern: SecurityPattern) -> List[Dict[str, Any]]:
        """Generate recommendations based on pattern type"""
        recommendations = []
        
        if pattern.pattern_type == "authentication_pattern":
            recommendations.extend([
                {
                    'priority': 'high',
                    'action': 'investigate_authentication',
                    'description': 'Investigate authentication anomalies and potential brute force attempts'
                },
                {
                    'priority': 'medium',
                    'action': 'enhance_authentication',
                    'description': 'Consider implementing additional authentication controls'
                }
            ])
        
        elif pattern.pattern_type == "privilege_pattern":
            recommendations.extend([
                {
                    'priority': 'high',
                    'action': 'review_privileges',
                    'description': 'Review and validate recent privilege changes'
                },
                {
                    'priority': 'medium',
                    'action': 'implement_approval',
                    'description': 'Implement approval workflow for privilege escalations'
                }
            ])
        
        elif pattern.pattern_type == "temporal_pattern":
            recommendations.extend([
                {
                    'priority': 'medium',
                    'action': 'verify_schedule',
                    'description': 'Verify if off-hours activity was scheduled or authorized'
                },
                {
                    'priority': 'low',
                    'action': 'adjust_monitoring',
                    'description': 'Adjust monitoring rules for expected off-hours activities'
                }
            ])
        
        return recommendations
    
    async def _store_security_insight(self, insight: SecurityInsight):
        """Store security insight in hAIveMind memory"""
        try:
            await self.memory_server.store_memory(
                content=json.dumps({
                    'insight_id': insight.insight_id,
                    'title': insight.title,
                    'description': insight.description,
                    'insight_type': insight.insight_type.value,
                    'confidence_score': insight.confidence_score,
                    'risk_score': insight.risk_score,
                    'impact_assessment': insight.impact_assessment,
                    'evidence': insight.evidence,
                    'recommendations': insight.recommendations,
                    'affected_entities': insight.affected_entities,
                    'created_at': insight.created_at.isoformat(),
                    'metadata': insight.metadata
                }),
                category='security',
                subcategory='security_insights',
                tags=['vault', 'analytics', 'security_insight', insight.insight_type.value],
                importance=insight.risk_score
            )
            
            # Store in local cache
            self.security_insights[insight.insight_id] = insight
            
        except Exception as e:
            self.logger.error(f"Error storing security insight: {str(e)}")
    
    async def _load_existing_baselines(self):
        """Load existing behavioral baselines"""
        try:
            # Load from hAIveMind memory
            baselines = await self.memory_server.search_memories(
                query="behavioral baseline",
                category="security",
                subcategory="behavioral_baselines",
                limit=1000
            )
            
            for baseline_memory in baselines:
                try:
                    baseline_data = json.loads(baseline_memory['content'])
                    baseline = BehavioralBaseline(
                        entity_id=baseline_data['entity_id'],
                        entity_type=baseline_data['entity_type'],
                        baseline_metrics=baseline_data['baseline_metrics'],
                        confidence_level=baseline_data['confidence_level'],
                        created_at=datetime.fromisoformat(baseline_data['created_at']),
                        updated_at=datetime.fromisoformat(baseline_data['updated_at']),
                        sample_size=baseline_data['sample_size'],
                        validity_period=timedelta(seconds=baseline_data['validity_period_seconds'])
                    )
                    self.behavioral_baselines[baseline.entity_id] = baseline
                except Exception as e:
                    self.logger.warning(f"Error loading baseline: {str(e)}")
            
            self.logger.info(f"Loaded {len(self.behavioral_baselines)} behavioral baselines")
            
        except Exception as e:
            self.logger.error(f"Error loading existing baselines: {str(e)}")
    
    async def _load_existing_patterns(self):
        """Load existing security patterns"""
        try:
            # Load from hAIveMind memory
            patterns = await self.memory_server.search_memories(
                query="security pattern",
                category="security",
                subcategory="security_patterns",
                limit=1000
            )
            
            for pattern_memory in patterns:
                try:
                    pattern_data = json.loads(pattern_memory['content'])
                    pattern = SecurityPattern(
                        pattern_id=pattern_data['pattern_id'],
                        pattern_type=pattern_data['pattern_type'],
                        name=pattern_data['name'],
                        description=pattern_data['description'],
                        indicators=pattern_data['indicators'],
                        confidence_score=pattern_data['confidence_score'],
                        risk_level=RiskLevel(pattern_data['risk_level']),
                        frequency=pattern_data['frequency'],
                        first_seen=datetime.fromisoformat(pattern_data['first_seen']),
                        last_seen=datetime.fromisoformat(pattern_data['last_seen']),
                        affected_resources=pattern_data['affected_resources'],
                        mitre_techniques=pattern_data.get('mitre_techniques', []),
                        metadata=pattern_data.get('metadata', {})
                    )
                    self.detected_patterns[pattern.pattern_id] = pattern
                except Exception as e:
                    self.logger.warning(f"Error loading pattern: {str(e)}")
            
            self.logger.info(f"Loaded {len(self.detected_patterns)} security patterns")
            
        except Exception as e:
            self.logger.error(f"Error loading existing patterns: {str(e)}")
    
    async def _initialize_ml_models(self):
        """Initialize machine learning models for analytics"""
        try:
            # Placeholder for ML model initialization
            # In production, this would load trained models for:
            # - Anomaly detection
            # - Pattern recognition
            # - Risk assessment
            # - Behavioral analysis
            
            self.logger.info("ML models initialized (placeholder)")
            
        except Exception as e:
            self.logger.error(f"Error initializing ML models: {str(e)}")
    
    async def _continuous_pattern_analysis(self):
        """Continuous pattern analysis background task"""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                # Analyze recent events for new patterns
                if len(self.event_buffer) > 100:
                    recent_events = list(self.event_buffer)[-100:]
                    await self._analyze_event_patterns(recent_events)
                
            except Exception as e:
                self.logger.error(f"Error in continuous pattern analysis: {str(e)}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _behavioral_analysis(self):
        """Behavioral analysis background task"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                # Update behavioral baselines
                for user_id, behaviors in self.user_behaviors.items():
                    if len(behaviors.get('events', [])) > 50:  # Sufficient data
                        await self._update_behavioral_baseline(user_id, behaviors)
                
            except Exception as e:
                self.logger.error(f"Error in behavioral analysis: {str(e)}")
                await asyncio.sleep(300)  # Wait before retrying
    
    async def _anomaly_detection_loop(self):
        """Anomaly detection background task"""
        while True:
            try:
                await asyncio.sleep(600)  # Run every 10 minutes
                
                # Run batch anomaly detection on recent events
                if len(self.event_buffer) > 50:
                    recent_events = list(self.event_buffer)[-50:]
                    await self._batch_anomaly_detection(recent_events)
                
            except Exception as e:
                self.logger.error(f"Error in anomaly detection loop: {str(e)}")
                await asyncio.sleep(120)  # Wait before retrying
    
    async def _insight_generation(self):
        """Insight generation background task"""
        while True:
            try:
                await asyncio.sleep(1800)  # Run every 30 minutes
                
                # Generate insights from accumulated data
                await self._generate_trend_insights()
                await self._generate_correlation_insights()
                
            except Exception as e:
                self.logger.error(f"Error in insight generation: {str(e)}")
                await asyncio.sleep(300)  # Wait before retrying
    
    async def _baseline_maintenance(self):
        """Baseline maintenance background task"""
        while True:
            try:
                await asyncio.sleep(86400)  # Run daily
                
                # Clean up old baselines and update existing ones
                await self._cleanup_old_baselines()
                await self._refresh_baselines()
                
            except Exception as e:
                self.logger.error(f"Error in baseline maintenance: {str(e)}")
                await asyncio.sleep(3600)  # Wait before retrying
    
    async def _analyze_event_patterns(self, events: List[Dict[str, Any]]):
        """Analyze events for new patterns"""
        # Placeholder for pattern analysis logic
        pass
    
    async def _update_behavioral_baseline(self, user_id: str, behaviors: Dict[str, Any]):
        """Update behavioral baseline for a user"""
        # Placeholder for baseline update logic
        pass
    
    async def _batch_anomaly_detection(self, events: List[Dict[str, Any]]):
        """Run batch anomaly detection"""
        # Placeholder for batch anomaly detection logic
        pass
    
    async def _generate_trend_insights(self):
        """Generate trend-based insights"""
        # Placeholder for trend analysis logic
        pass
    
    async def _generate_correlation_insights(self):
        """Generate correlation-based insights"""
        # Placeholder for correlation analysis logic
        pass
    
    async def _cleanup_old_baselines(self):
        """Clean up old behavioral baselines"""
        # Placeholder for baseline cleanup logic
        pass
    
    async def _refresh_baselines(self):
        """Refresh existing baselines"""
        # Placeholder for baseline refresh logic
        pass


# Integration with existing hAIveMind vault integration
class EnhancedHAIveMindIntegration:
    """Enhanced hAIveMind integration with advanced analytics"""
    
    def __init__(self, config: Dict[str, Any], redis_client: redis.Redis, 
                 memory_server: MemoryMCPServer):
        self.config = config
        self.redis = redis_client
        self.memory_server = memory_server
        self.logger = logging.getLogger(__name__)
        
        # Initialize analytics engine
        self.analytics = AdvancedSecurityAnalytics(redis_client, memory_server)
    
    async def initialize(self) -> bool:
        """Initialize enhanced hAIveMind integration"""
        try:
            # Initialize analytics engine
            if not await self.analytics.initialize_analytics():
                return False
            
            self.logger.info("Enhanced hAIveMind integration initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize enhanced integration: {str(e)}")
            return False
    
    async def process_vault_event(self, event: Dict[str, Any]) -> List[SecurityInsight]:
        """Process vault event with enhanced analytics"""
        try:
            # Process event through analytics engine
            insights = await self.analytics.process_security_event(event)
            
            # Broadcast high-risk insights to hAIveMind network
            for insight in insights:
                if insight.risk_score >= 0.7:  # High risk threshold
                    await self._broadcast_security_insight(insight)
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error processing vault event: {str(e)}")
            return []
    
    async def _broadcast_security_insight(self, insight: SecurityInsight):
        """Broadcast security insight to hAIveMind network"""
        try:
            broadcast_data = {
                'message_type': 'security_insight',
                'source': 'vault_security_agent',
                'insight_id': insight.insight_id,
                'title': insight.title,
                'description': insight.description,
                'risk_score': insight.risk_score,
                'confidence_score': insight.confidence_score,
                'affected_entities': insight.affected_entities,
                'recommendations': insight.recommendations[:3],  # Top 3 recommendations
                'timestamp': insight.created_at.isoformat()
            }
            
            await self.memory_server.store_memory(
                content=json.dumps(broadcast_data),
                category='security',
                subcategory='haivemind_broadcast',
                tags=['vault', 'security_insight', 'broadcast', 'high_risk'],
                importance=insight.risk_score
            )
            
            self.logger.info(f"Broadcasted security insight {insight.insight_id} to hAIveMind network")
            
        except Exception as e:
            self.logger.error(f"Error broadcasting security insight: {str(e)}")


# Example usage
async def main():
    """Example usage of enhanced hAIveMind analytics"""
    import redis.asyncio as redis
    from ..memory_server import MemoryMCPServer
    
    # Configuration
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    
    # Mock memory server (in production, use actual MemoryMCPServer)
    class MockMemoryServer:
        async def store_memory(self, **kwargs):
            print(f"Storing memory: {kwargs['category']}/{kwargs['subcategory']}")
        
        async def search_memories(self, **kwargs):
            return []
    
    memory_server = MockMemoryServer()
    
    # Initialize enhanced integration
    config = {'machine_id': 'test-machine'}
    enhanced_integration = EnhancedHAIveMindIntegration(config, redis_client, memory_server)
    
    if await enhanced_integration.initialize():
        print("✅ Enhanced hAIveMind integration initialized")
        
        # Example security event
        test_event = {
            'event_id': 'test-001',
            'event_type': 'credential_access',
            'user_id': 'user-123',
            'credential_id': 'cred-456',
            'action': 'retrieve_credential',
            'result': 'success',
            'timestamp': datetime.utcnow(),
            'ip_address': '192.168.1.100',
            'user_agent': 'VaultClient/1.0'
        }
        
        # Process event
        insights = await enhanced_integration.process_vault_event(test_event)
        
        print(f"✅ Generated {len(insights)} security insights")
        for insight in insights:
            print(f"   - {insight.title} (Risk: {insight.risk_score:.2f})")
    else:
        print("❌ Failed to initialize enhanced hAIveMind integration")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())