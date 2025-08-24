#!/usr/bin/env python3
"""
MCP Hub Security hAIveMind Integration
Advanced security analytics, anomaly detection, and threat intelligence
"""

import asyncio
import json
import logging
import time
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

@dataclass
class SecurityPattern:
    """Detected security pattern"""
    pattern_type: str
    severity: str  # low, medium, high, critical
    description: str
    indicators: List[str]
    confidence: float
    first_seen: datetime
    last_seen: datetime
    occurrence_count: int
    affected_users: List[str]
    affected_servers: List[str]
    recommended_actions: List[str]

@dataclass
class ThreatIntelligence:
    """Threat intelligence data"""
    threat_type: str
    source: str
    confidence: float
    description: str
    indicators: Dict[str, Any]
    mitigation_steps: List[str]
    created_at: datetime

class MCPSecurityHAIveMind:
    """hAIveMind-powered security analytics and threat detection"""
    
    def __init__(self, auth_manager, memory_storage):
        self.auth_manager = auth_manager
        self.memory_storage = memory_storage
        
        # Pattern detection state
        self.user_behavior_profiles = defaultdict(lambda: {
            'login_times': deque(maxlen=100),
            'tool_usage': defaultdict(int),
            'ip_addresses': deque(maxlen=50),
            'failed_attempts': deque(maxlen=20),
            'session_durations': deque(maxlen=50),
            'risk_score': 0.0
        })
        
        self.detected_patterns = []
        self.threat_intelligence = []
        
        # Anomaly detection thresholds
        self.anomaly_thresholds = {
            'failed_login_rate': 5,  # per hour
            'unusual_login_time': 0.1,  # probability threshold
            'new_ip_frequency': 3,  # new IPs per day
            'tool_usage_spike': 3.0,  # standard deviations
            'session_duration_anomaly': 2.5,  # standard deviations
            'privilege_escalation_attempts': 1  # any attempt
        }
        
        logger.info("🧠 MCP Security hAIveMind initialized")
    
    async def analyze_authentication_event(self, event_data: Dict[str, Any]) -> List[SecurityPattern]:
        """Analyze authentication events for security patterns"""
        patterns = []
        
        user_id = event_data.get('user_id')
        client_ip = event_data.get('client_ip')
        event_type = event_data.get('event_type')
        success = event_data.get('success', False)
        timestamp = datetime.fromtimestamp(event_data.get('timestamp', time.time()))
        
        if not user_id:
            return patterns
        
        profile = self.user_behavior_profiles[user_id]
        
        # Update user profile
        if event_type in ['login_success', 'login_failed']:
            profile['login_times'].append(timestamp)
            if client_ip:
                profile['ip_addresses'].append(client_ip)
            
            if not success:
                profile['failed_attempts'].append(timestamp)
        
        # Detect brute force attacks
        if event_type == 'login_failed':
            recent_failures = [t for t in profile['failed_attempts'] 
                             if timestamp - t < timedelta(hours=1)]
            
            if len(recent_failures) >= self.anomaly_thresholds['failed_login_rate']:
                patterns.append(SecurityPattern(
                    pattern_type='brute_force_attack',
                    severity='high',
                    description=f'Brute force attack detected for user {user_id}',
                    indicators=[f'{len(recent_failures)} failed attempts in 1 hour'],
                    confidence=0.9,
                    first_seen=min(recent_failures),
                    last_seen=timestamp,
                    occurrence_count=len(recent_failures),
                    affected_users=[user_id],
                    affected_servers=[],
                    recommended_actions=[
                        'Temporarily lock user account',
                        'Require password reset',
                        'Enable MFA if not already active',
                        'Block source IP address'
                    ]
                ))
        
        # Detect unusual login times
        if event_type == 'login_success' and len(profile['login_times']) > 10:
            login_hours = [t.hour for t in profile['login_times']]
            current_hour = timestamp.hour
            
            # Calculate probability of login at this hour
            hour_frequency = login_hours.count(current_hour) / len(login_hours)
            
            if hour_frequency < self.anomaly_thresholds['unusual_login_time']:
                patterns.append(SecurityPattern(
                    pattern_type='unusual_login_time',
                    severity='medium',
                    description=f'Unusual login time detected for user {user_id}',
                    indicators=[f'Login at {current_hour}:00, typical frequency: {hour_frequency:.2%}'],
                    confidence=0.7,
                    first_seen=timestamp,
                    last_seen=timestamp,
                    occurrence_count=1,
                    affected_users=[user_id],
                    affected_servers=[],
                    recommended_actions=[
                        'Verify user identity',
                        'Check for account compromise',
                        'Review recent activity'
                    ]
                ))
        
        # Detect new IP addresses
        if client_ip and event_type == 'login_success':
            unique_ips = set(profile['ip_addresses'])
            recent_ips = [ip for ip, t in zip(profile['ip_addresses'], profile['login_times'])
                         if timestamp - t < timedelta(days=1)]
            
            if client_ip not in unique_ips and len(set(recent_ips)) > self.anomaly_thresholds['new_ip_frequency']:
                patterns.append(SecurityPattern(
                    pattern_type='multiple_new_ips',
                    severity='medium',
                    description=f'Multiple new IP addresses for user {user_id}',
                    indicators=[f'{len(set(recent_ips))} different IPs in 24 hours'],
                    confidence=0.6,
                    first_seen=timestamp,
                    last_seen=timestamp,
                    occurrence_count=len(set(recent_ips)),
                    affected_users=[user_id],
                    affected_servers=[],
                    recommended_actions=[
                        'Verify user travel/location changes',
                        'Check for credential sharing',
                        'Enable location-based alerts'
                    ]
                ))
        
        # Store patterns in hAIveMind
        for pattern in patterns:
            await self._store_security_pattern(pattern)
        
        return patterns
    
    async def analyze_tool_execution_event(self, event_data: Dict[str, Any]) -> List[SecurityPattern]:
        """Analyze tool execution events for security patterns"""
        patterns = []
        
        user_id = event_data.get('user_id')
        tool_name = event_data.get('tool_name')
        server_id = event_data.get('server_id')
        success = event_data.get('success', False)
        timestamp = datetime.fromtimestamp(event_data.get('timestamp', time.time()))
        
        if not user_id or not tool_name:
            return patterns
        
        profile = self.user_behavior_profiles[user_id]
        profile['tool_usage'][tool_name] += 1
        
        # Detect privilege escalation attempts
        high_privilege_tools = [
            'delete_memory', 'bulk_delete_memories', 'gdpr_delete_user_data',
            'create_user_account', 'create_api_key', 'configure_server_auth'
        ]
        
        if tool_name in high_privilege_tools and not success:
            patterns.append(SecurityPattern(
                pattern_type='privilege_escalation_attempt',
                severity='high',
                description=f'Privilege escalation attempt by user {user_id}',
                indicators=[f'Failed attempt to use {tool_name}'],
                confidence=0.8,
                first_seen=timestamp,
                last_seen=timestamp,
                occurrence_count=1,
                affected_users=[user_id],
                affected_servers=[server_id] if server_id else [],
                recommended_actions=[
                    'Review user permissions',
                    'Investigate user intent',
                    'Consider role adjustment',
                    'Monitor future activity closely'
                ]
            ))
        
        # Detect unusual tool usage spikes
        if len(profile['tool_usage']) > 5:
            usage_counts = list(profile['tool_usage'].values())
            mean_usage = statistics.mean(usage_counts)
            std_usage = statistics.stdev(usage_counts) if len(usage_counts) > 1 else 0
            
            current_usage = profile['tool_usage'][tool_name]
            
            if std_usage > 0 and (current_usage - mean_usage) / std_usage > self.anomaly_thresholds['tool_usage_spike']:
                patterns.append(SecurityPattern(
                    pattern_type='unusual_tool_usage',
                    severity='medium',
                    description=f'Unusual tool usage spike for user {user_id}',
                    indicators=[f'{tool_name} used {current_usage} times (avg: {mean_usage:.1f})'],
                    confidence=0.6,
                    first_seen=timestamp,
                    last_seen=timestamp,
                    occurrence_count=current_usage,
                    affected_users=[user_id],
                    affected_servers=[server_id] if server_id else [],
                    recommended_actions=[
                        'Verify legitimate use case',
                        'Check for automation/scripting',
                        'Review tool necessity'
                    ]
                ))
        
        # Store patterns in hAIveMind
        for pattern in patterns:
            await self._store_security_pattern(pattern)
        
        return patterns
    
    async def generate_threat_intelligence(self, patterns: List[SecurityPattern]) -> List[ThreatIntelligence]:
        """Generate threat intelligence from detected patterns"""
        threats = []
        
        # Group patterns by type
        pattern_groups = defaultdict(list)
        for pattern in patterns:
            pattern_groups[pattern.pattern_type].append(pattern)
        
        # Analyze brute force patterns
        if 'brute_force_attack' in pattern_groups:
            brute_force_patterns = pattern_groups['brute_force_attack']
            affected_users = set()
            source_ips = set()
            
            for pattern in brute_force_patterns:
                affected_users.update(pattern.affected_users)
                # Extract IPs from indicators if available
                for indicator in pattern.indicators:
                    if 'IP' in indicator:
                        # This would need more sophisticated IP extraction
                        pass
            
            if len(brute_force_patterns) > 1:
                threats.append(ThreatIntelligence(
                    threat_type='coordinated_brute_force',
                    source='pattern_analysis',
                    confidence=0.8,
                    description=f'Coordinated brute force attack affecting {len(affected_users)} users',
                    indicators={
                        'affected_users': list(affected_users),
                        'attack_count': len(brute_force_patterns),
                        'time_window': '1 hour'
                    },
                    mitigation_steps=[
                        'Implement account lockout policies',
                        'Deploy rate limiting',
                        'Enable MFA for all accounts',
                        'Block malicious IP ranges'
                    ],
                    created_at=datetime.now()
                ))
        
        # Analyze privilege escalation patterns
        if 'privilege_escalation_attempt' in pattern_groups:
            escalation_patterns = pattern_groups['privilege_escalation_attempt']
            
            threats.append(ThreatIntelligence(
                threat_type='privilege_escalation_campaign',
                source='pattern_analysis',
                confidence=0.7,
                description=f'Privilege escalation attempts detected',
                indicators={
                    'attempt_count': len(escalation_patterns),
                    'affected_tools': list(set(p.indicators[0] for p in escalation_patterns))
                },
                mitigation_steps=[
                    'Review and tighten role permissions',
                    'Implement principle of least privilege',
                    'Add additional approval workflows',
                    'Monitor privileged operations'
                ],
                created_at=datetime.now()
            ))
        
        # Store threat intelligence in hAIveMind
        for threat in threats:
            await self._store_threat_intelligence(threat)
        
        return threats
    
    async def calculate_user_risk_score(self, user_id: str) -> float:
        """Calculate dynamic risk score for a user"""
        profile = self.user_behavior_profiles[user_id]
        risk_score = 0.0
        
        # Failed login attempts (last 24 hours)
        recent_failures = [t for t in profile['failed_attempts'] 
                          if datetime.now() - t < timedelta(hours=24)]
        risk_score += min(len(recent_failures) * 10, 50)  # Max 50 points
        
        # IP address diversity (last 7 days)
        recent_ips = [ip for ip, t in zip(profile['ip_addresses'], profile['login_times'])
                     if datetime.now() - t < timedelta(days=7)]
        unique_recent_ips = len(set(recent_ips))
        if unique_recent_ips > 3:
            risk_score += min((unique_recent_ips - 3) * 5, 25)  # Max 25 points
        
        # Unusual login times
        if len(profile['login_times']) > 10:
            login_hours = [t.hour for t in profile['login_times'][-10:]]
            hour_variance = statistics.variance(login_hours) if len(set(login_hours)) > 1 else 0
            if hour_variance > 50:  # High variance in login times
                risk_score += 15
        
        # Tool usage patterns
        high_risk_tools = ['delete_memory', 'bulk_delete_memories', 'gdpr_delete_user_data']
        high_risk_usage = sum(profile['tool_usage'].get(tool, 0) for tool in high_risk_tools)
        risk_score += min(high_risk_usage * 5, 20)  # Max 20 points
        
        # Normalize to 0-100 scale
        risk_score = min(risk_score, 100)
        
        # Update profile
        profile['risk_score'] = risk_score
        
        # Store risk score update in hAIveMind
        await self.memory_storage.store_memory(
            content=f"User risk score updated: {user_id} = {risk_score:.1f}",
            category='security',
            metadata={
                'event_type': 'risk_score_update',
                'user_id': user_id,
                'risk_score': risk_score,
                'factors': {
                    'recent_failures': len(recent_failures),
                    'unique_ips': unique_recent_ips,
                    'high_risk_tool_usage': high_risk_usage
                },
                'timestamp': time.time()
            },
            scope='hive-shared'
        )
        
        return risk_score
    
    async def get_security_recommendations(self) -> List[Dict[str, Any]]:
        """Generate security recommendations based on analysis"""
        recommendations = []
        
        # Analyze overall patterns
        high_risk_users = [uid for uid, profile in self.user_behavior_profiles.items() 
                          if profile['risk_score'] > 70]
        
        if high_risk_users:
            recommendations.append({
                'type': 'high_risk_users',
                'severity': 'high',
                'title': f'{len(high_risk_users)} High-Risk Users Detected',
                'description': 'Users with elevated risk scores require attention',
                'affected_users': high_risk_users,
                'actions': [
                    'Review user activities',
                    'Consider additional authentication requirements',
                    'Implement enhanced monitoring'
                ]
            })
        
        # Check for common attack patterns
        recent_patterns = [p for p in self.detected_patterns 
                          if datetime.now() - p.last_seen < timedelta(hours=24)]
        
        pattern_types = defaultdict(int)
        for pattern in recent_patterns:
            pattern_types[pattern.pattern_type] += 1
        
        if pattern_types['brute_force_attack'] > 0:
            recommendations.append({
                'type': 'brute_force_protection',
                'severity': 'high',
                'title': 'Brute Force Attacks Detected',
                'description': f'{pattern_types["brute_force_attack"]} brute force attempts in 24 hours',
                'actions': [
                    'Enable account lockout policies',
                    'Implement progressive delays',
                    'Deploy IP-based rate limiting',
                    'Consider CAPTCHA implementation'
                ]
            })
        
        if pattern_types['privilege_escalation_attempt'] > 0:
            recommendations.append({
                'type': 'privilege_review',
                'severity': 'medium',
                'title': 'Privilege Escalation Attempts',
                'description': f'{pattern_types["privilege_escalation_attempt"]} escalation attempts detected',
                'actions': [
                    'Review user role assignments',
                    'Audit permission grants',
                    'Implement approval workflows',
                    'Add privilege usage monitoring'
                ]
            })
        
        # Store recommendations in hAIveMind
        if recommendations:
            await self.memory_storage.store_memory(
                content=f"Security recommendations generated: {len(recommendations)} items",
                category='security',
                metadata={
                    'event_type': 'security_recommendations',
                    'recommendation_count': len(recommendations),
                    'recommendations': recommendations,
                    'timestamp': time.time()
                },
                scope='hive-shared'
            )
        
        return recommendations
    
    async def _store_security_pattern(self, pattern: SecurityPattern):
        """Store detected security pattern in hAIveMind"""
        try:
            self.detected_patterns.append(pattern)
            
            await self.memory_storage.store_memory(
                content=f"Security pattern detected: {pattern.pattern_type}",
                category='security',
                metadata={
                    'event_type': 'security_pattern_detected',
                    'pattern_type': pattern.pattern_type,
                    'severity': pattern.severity,
                    'confidence': pattern.confidence,
                    'affected_users': pattern.affected_users,
                    'affected_servers': pattern.affected_servers,
                    'indicators': pattern.indicators,
                    'recommended_actions': pattern.recommended_actions,
                    'timestamp': time.time()
                },
                scope='hive-shared'
            )
            
            # Broadcast high-severity patterns
            if pattern.severity in ['high', 'critical']:
                await self.memory_storage.broadcast_discovery(
                    message=f"High-severity security pattern: {pattern.description}",
                    category='security_alert',
                    severity='critical' if pattern.severity == 'critical' else 'warning'
                )
        
        except Exception as e:
            logger.error(f"Error storing security pattern: {e}")
    
    async def _store_threat_intelligence(self, threat: ThreatIntelligence):
        """Store threat intelligence in hAIveMind"""
        try:
            self.threat_intelligence.append(threat)
            
            await self.memory_storage.store_memory(
                content=f"Threat intelligence: {threat.threat_type}",
                category='security',
                metadata={
                    'event_type': 'threat_intelligence',
                    'threat_type': threat.threat_type,
                    'source': threat.source,
                    'confidence': threat.confidence,
                    'indicators': threat.indicators,
                    'mitigation_steps': threat.mitigation_steps,
                    'timestamp': time.time()
                },
                scope='hive-shared'
            )
            
            # Broadcast high-confidence threats
            if threat.confidence > 0.7:
                await self.memory_storage.broadcast_discovery(
                    message=f"High-confidence threat detected: {threat.description}",
                    category='threat_intelligence',
                    severity='critical'
                )
        
        except Exception as e:
            logger.error(f"Error storing threat intelligence: {e}")
    
    async def run_continuous_analysis(self):
        """Run continuous security analysis"""
        logger.info("🔍 Starting continuous security analysis")
        
        while True:
            try:
                # Generate recommendations every hour
                recommendations = await self.get_security_recommendations()
                
                if recommendations:
                    logger.info(f"Generated {len(recommendations)} security recommendations")
                
                # Calculate risk scores for active users
                for user_id in list(self.user_behavior_profiles.keys()):
                    await self.calculate_user_risk_score(user_id)
                
                # Clean up old patterns (keep last 30 days)
                cutoff_time = datetime.now() - timedelta(days=30)
                self.detected_patterns = [p for p in self.detected_patterns 
                                        if p.last_seen > cutoff_time]
                
                # Sleep for 1 hour
                await asyncio.sleep(3600)
            
            except Exception as e:
                logger.error(f"Error in continuous security analysis: {e}")
                await asyncio.sleep(300)  # Sleep 5 minutes on error