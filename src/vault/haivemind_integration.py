"""
hAIveMind Integration for Vault Security Events and Threat Intelligence
Integrates with the hAIveMind system for distributed security intelligence.

Author: Lance James, Unit 221B
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import secrets
import hashlib
import redis
from ..memory_server import MemoryMCPServer


class ThreatIntelType(Enum):
    """Types of threat intelligence"""
    IOC = "indicator_of_compromise"
    TTP = "tactics_techniques_procedures"
    VULNERABILITY = "vulnerability"
    CAMPAIGN = "campaign"
    ACTOR = "threat_actor"
    MALWARE = "malware"
    ATTACK_PATTERN = "attack_pattern"
    INFRASTRUCTURE = "infrastructure"


class SecurityEventCategory(Enum):
    """Categories of security events for hAIveMind"""
    AUTHENTICATION_ANOMALY = "authentication_anomaly"
    CREDENTIAL_COMPROMISE = "credential_compromise"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    LATERAL_MOVEMENT = "lateral_movement"
    PERSISTENCE_MECHANISM = "persistence_mechanism"
    DEFENSE_EVASION = "defense_evasion"
    RECONNAISSANCE = "reconnaissance"
    IMPACT_EVENT = "impact_event"


class IntelligenceClassification(Enum):
    """Classification levels for threat intelligence"""
    TLP_WHITE = "tlp_white"    # Can be shared freely
    TLP_GREEN = "tlp_green"    # Community sharing
    TLP_AMBER = "tlp_amber"    # Limited sharing
    TLP_RED = "tlp_red"        # Restricted sharing


@dataclass
class ThreatIntelligence:
    """Threat intelligence data structure"""
    intel_id: str
    intel_type: ThreatIntelType
    title: str
    description: str
    indicators: List[Dict[str, Any]]
    confidence: float  # 0.0 to 1.0
    severity: str
    classification: IntelligenceClassification
    source: str
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]
    tags: List[str] = field(default_factory=list)
    mitre_tactics: List[str] = field(default_factory=list)
    mitre_techniques: List[str] = field(default_factory=list)
    related_campaigns: List[str] = field(default_factory=list)
    attribution: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityInsight:
    """Security insight derived from events and intelligence"""
    insight_id: str
    title: str
    description: str
    insight_type: str
    confidence_score: float
    risk_score: float
    affected_systems: List[str]
    related_events: List[str]
    related_intel: List[str]
    recommendations: List[str]
    created_at: datetime
    created_by: str
    validated: bool = False
    false_positive: bool = False


@dataclass
class CollaborativeResponse:
    """Coordinated response across hAIveMind network"""
    response_id: str
    threat_category: SecurityEventCategory
    threat_description: str
    affected_assets: List[str]
    response_actions: List[Dict[str, Any]]
    participating_agents: List[str]
    coordination_status: str
    initiated_at: datetime
    completed_at: Optional[datetime] = None


class HAIveMindVaultIntegration:
    """hAIveMind integration for vault security and threat intelligence"""
    
    def __init__(self, config: Dict[str, Any], redis_client: redis.Redis, 
                 memory_server: MemoryMCPServer):
        self.config = config
        self.redis = redis_client
        self.memory_server = memory_server
        self.logger = logging.getLogger(__name__)
        
        self.threat_intelligence: Dict[str, ThreatIntelligence] = {}
        self.security_insights: Dict[str, SecurityInsight] = {}
        self.collaborative_responses: Dict[str, CollaborativeResponse] = {}
        self.agent_capabilities: Dict[str, Set[str]] = {}
        self.intelligence_feeds: List[str] = []
        
    async def initialize_haivemind_integration(self) -> bool:
        """Initialize hAIveMind integration"""
        try:
            await self._register_vault_agent()
            await self._initialize_threat_intelligence_feeds()
            await self._load_existing_intelligence()
            await self._setup_event_correlation()
            
            # Start background tasks
            asyncio.create_task(self._threat_intelligence_updater())
            asyncio.create_task(self._collaborative_analysis())
            asyncio.create_task(self._intelligence_sharing())
            
            self.logger.info("hAIveMind integration initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize hAIveMind integration: {str(e)}")
            return False
    
    async def _register_vault_agent(self) -> None:
        """Register vault agent with hAIveMind network"""
        try:
            agent_info = {
                'agent_id': 'vault_security_agent',
                'agent_type': 'security_vault',
                'capabilities': [
                    'credential_monitoring',
                    'access_control',
                    'authentication_analysis',
                    'privilege_management',
                    'security_compliance',
                    'threat_detection',
                    'anomaly_detection',
                    'incident_response'
                ],
                'specialization': 'credential_security',
                'machine_id': self.config.get('machine_id', 'unknown'),
                'status': 'active',
                'last_heartbeat': datetime.utcnow().isoformat()
            }
            
            await self.memory_server.store_memory(
                content=json.dumps(agent_info),
                category='agent',
                subcategory='registration',
                tags=['vault', 'security', 'agent_registration'],
                importance=0.9
            )
            
            self.logger.info("Vault agent registered with hAIveMind")
            
        except Exception as e:
            self.logger.error(f"Failed to register vault agent: {str(e)}")
    
    async def _initialize_threat_intelligence_feeds(self) -> None:
        """Initialize threat intelligence feeds"""
        try:
            feeds_config = self.config.get('vault', {}).get('threat_intel_feeds', [])
            
            default_feeds = [
                {
                    'name': 'internal_vault_intel',
                    'type': 'internal',
                    'description': 'Internal vault security intelligence'
                },
                {
                    'name': 'haivemind_collective_intel',
                    'type': 'collective',
                    'description': 'Collective intelligence from hAIveMind network'
                },
                {
                    'name': 'mitre_attack',
                    'type': 'external',
                    'description': 'MITRE ATT&CK framework data'
                }
            ]
            
            self.intelligence_feeds = feeds_config or default_feeds
            
            for feed in self.intelligence_feeds:
                await self._initialize_intelligence_feed(feed)
            
        except Exception as e:
            self.logger.error(f"Failed to initialize threat intelligence feeds: {str(e)}")
    
    async def _initialize_intelligence_feed(self, feed_config: Dict[str, Any]) -> None:
        """Initialize a specific threat intelligence feed"""
        try:
            feed_info = {
                'feed_name': feed_config['name'],
                'feed_type': feed_config['type'],
                'description': feed_config['description'],
                'status': 'active',
                'last_update': datetime.utcnow().isoformat(),
                'intelligence_count': 0
            }
            
            await self.memory_server.store_memory(
                content=json.dumps(feed_info),
                category='infrastructure',
                subcategory='threat_intelligence_feed',
                tags=['threat_intel', 'feed', feed_config['name']],
                importance=0.8
            )
            
        except Exception as e:
            self.logger.error(f"Failed to initialize feed {feed_config['name']}: {str(e)}")
    
    async def _load_existing_intelligence(self) -> None:
        """Load existing threat intelligence from hAIveMind"""
        try:
            search_results = await self.memory_server.search_memories(
                query="threat intelligence vault security",
                category="security",
                limit=1000
            )
            
            for memory in search_results.get('memories', []):
                try:
                    intel_data = json.loads(memory['content'])
                    if 'intel_id' in intel_data:
                        intel = ThreatIntelligence(
                            intel_id=intel_data['intel_id'],
                            intel_type=ThreatIntelType(intel_data['intel_type']),
                            title=intel_data['title'],
                            description=intel_data['description'],
                            indicators=intel_data['indicators'],
                            confidence=intel_data['confidence'],
                            severity=intel_data['severity'],
                            classification=IntelligenceClassification(intel_data['classification']),
                            source=intel_data['source'],
                            created_at=datetime.fromisoformat(intel_data['created_at']),
                            updated_at=datetime.fromisoformat(intel_data['updated_at']),
                            expires_at=datetime.fromisoformat(intel_data['expires_at']) if intel_data.get('expires_at') else None,
                            tags=intel_data.get('tags', []),
                            mitre_tactics=intel_data.get('mitre_tactics', []),
                            mitre_techniques=intel_data.get('mitre_techniques', [])
                        )
                        self.threat_intelligence[intel.intel_id] = intel
                        
                except Exception as e:
                    self.logger.error(f"Failed to parse intelligence memory: {str(e)}")
            
            self.logger.info(f"Loaded {len(self.threat_intelligence)} threat intelligence items")
            
        except Exception as e:
            self.logger.error(f"Failed to load existing intelligence: {str(e)}")
    
    async def _setup_event_correlation(self) -> None:
        """Setup event correlation with threat intelligence"""
        try:
            correlation_config = {
                'correlation_rules': [
                    {
                        'rule_id': 'credential_compromise_indicators',
                        'description': 'Correlate access patterns with credential compromise indicators',
                        'event_types': ['authentication_failure', 'unusual_access_pattern'],
                        'intelligence_types': ['IOC', 'TTP'],
                        'threshold': 0.7
                    },
                    {
                        'rule_id': 'privilege_escalation_detection',
                        'description': 'Detect privilege escalation attempts',
                        'event_types': ['privilege_change', 'elevated_access'],
                        'intelligence_types': ['ATTACK_PATTERN', 'TTP'],
                        'threshold': 0.8
                    }
                ]
            }
            
            await self.memory_server.store_memory(
                content=json.dumps(correlation_config),
                category='infrastructure',
                subcategory='correlation_rules',
                tags=['correlation', 'threat_detection', 'vault'],
                importance=0.9
            )
            
        except Exception as e:
            self.logger.error(f"Failed to setup event correlation: {str(e)}")
    
    async def process_security_event(self, event_data: Dict[str, Any]) -> List[SecurityInsight]:
        """Process security event and generate insights"""
        try:
            insights = []
            
            # Store event in hAIveMind for collective learning
            await self._store_security_event(event_data)
            
            # Correlate with threat intelligence
            correlated_intel = await self._correlate_with_intelligence(event_data)
            
            # Generate insights
            for intel in correlated_intel:
                insight = await self._generate_security_insight(event_data, intel)
                if insight:
                    insights.append(insight)
                    await self._store_security_insight(insight)
            
            # Broadcast significant events to hAIveMind network
            if insights and max(insight.risk_score for insight in insights) > 0.7:
                await self._broadcast_security_discovery(event_data, insights)
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Failed to process security event: {str(e)}")
            return []
    
    async def _store_security_event(self, event_data: Dict[str, Any]) -> None:
        """Store security event in hAIveMind"""
        try:
            event_memory = {
                'event_id': event_data.get('event_id', secrets.token_hex(8)),
                'timestamp': event_data.get('timestamp', datetime.utcnow().isoformat()),
                'event_type': event_data.get('event_type'),
                'severity': event_data.get('severity'),
                'user_id': event_data.get('user_id'),
                'credential_id': event_data.get('credential_id'),
                'source_ip': event_data.get('source_ip'),
                'action': event_data.get('action'),
                'result': event_data.get('result'),
                'anomaly_score': event_data.get('anomaly_score', 0.0),
                'context': event_data.get('context', {}),
                'machine_id': self.config.get('machine_id', 'unknown')
            }
            
            await self.memory_server.store_memory(
                content=json.dumps(event_memory),
                category='security',
                subcategory='vault_event',
                tags=['vault', 'security_event', event_data.get('event_type', 'unknown')],
                importance=min(0.9, 0.3 + event_data.get('anomaly_score', 0.0))
            )
            
        except Exception as e:
            self.logger.error(f"Failed to store security event: {str(e)}")
    
    async def _correlate_with_intelligence(self, event_data: Dict[str, Any]) -> List[ThreatIntelligence]:
        """Correlate event with threat intelligence"""
        correlated_intel = []
        
        try:
            event_indicators = self._extract_event_indicators(event_data)
            
            for intel_id, intel in self.threat_intelligence.items():
                correlation_score = await self._calculate_correlation_score(
                    event_indicators, intel.indicators
                )
                
                if correlation_score > 0.5:  # Threshold for correlation
                    correlated_intel.append(intel)
            
            # Also search hAIveMind for related intelligence
            search_query = f"threat intelligence {event_data.get('event_type', '')} {event_data.get('source_ip', '')}"
            
            search_results = await self.memory_server.search_memories(
                query=search_query,
                category="security",
                limit=50
            )
            
            for memory in search_results.get('memories', []):
                if 'threat_intelligence' in memory.get('tags', []):
                    # Process additional intelligence from network
                    pass
            
        except Exception as e:
            self.logger.error(f"Failed to correlate with intelligence: {str(e)}")
        
        return correlated_intel
    
    def _extract_event_indicators(self, event_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract indicators from security event"""
        indicators = []
        
        if event_data.get('source_ip'):
            indicators.append({
                'type': 'ipv4-addr',
                'value': event_data['source_ip'],
                'context': 'source_ip'
            })
        
        if event_data.get('user_agent'):
            indicators.append({
                'type': 'user-agent',
                'value': event_data['user_agent'],
                'context': 'user_agent'
            })
        
        if event_data.get('user_id'):
            indicators.append({
                'type': 'user-account',
                'value': event_data['user_id'],
                'context': 'user_account'
            })
        
        return indicators
    
    async def _calculate_correlation_score(self, event_indicators: List[Dict[str, Any]], 
                                         intel_indicators: List[Dict[str, Any]]) -> float:
        """Calculate correlation score between event and intelligence indicators"""
        if not event_indicators or not intel_indicators:
            return 0.0
        
        matches = 0
        total_comparisons = 0
        
        for event_indicator in event_indicators:
            for intel_indicator in intel_indicators:
                total_comparisons += 1
                
                if (event_indicator.get('type') == intel_indicator.get('type') and
                    event_indicator.get('value') == intel_indicator.get('value')):
                    matches += 1
                elif self._similar_indicators(event_indicator, intel_indicator):
                    matches += 0.5  # Partial match
        
        return matches / max(total_comparisons, 1)
    
    def _similar_indicators(self, indicator1: Dict[str, Any], indicator2: Dict[str, Any]) -> bool:
        """Check if indicators are similar"""
        if indicator1.get('type') != indicator2.get('type'):
            return False
        
        value1 = str(indicator1.get('value', '')).lower()
        value2 = str(indicator2.get('value', '')).lower()
        
        # Simple similarity check (could be enhanced with fuzzy matching)
        if indicator1.get('type') == 'ipv4-addr':
            # Check if IPs are in same subnet
            try:
                ip1_parts = value1.split('.')
                ip2_parts = value2.split('.')
                if len(ip1_parts) >= 3 and len(ip2_parts) >= 3:
                    return ip1_parts[:3] == ip2_parts[:3]  # Same /24 subnet
            except:
                pass
        
        return False
    
    async def _generate_security_insight(self, event_data: Dict[str, Any], 
                                       intelligence: ThreatIntelligence) -> Optional[SecurityInsight]:
        """Generate security insight from event and intelligence correlation"""
        try:
            confidence_score = min(0.9, intelligence.confidence + 0.1)
            risk_score = self._calculate_risk_score(event_data, intelligence)
            
            insight = SecurityInsight(
                insight_id=secrets.token_hex(16),
                title=f"Potential threat activity: {intelligence.title}",
                description=f"Security event correlates with known threat intelligence: {intelligence.description}",
                insight_type="threat_correlation",
                confidence_score=confidence_score,
                risk_score=risk_score,
                affected_systems=[event_data.get('source_ip', 'unknown')],
                related_events=[event_data.get('event_id', 'unknown')],
                related_intel=[intelligence.intel_id],
                recommendations=self._generate_recommendations(event_data, intelligence),
                created_at=datetime.utcnow(),
                created_by='vault_security_agent'
            )
            
            return insight
            
        except Exception as e:
            self.logger.error(f"Failed to generate security insight: {str(e)}")
            return None
    
    def _calculate_risk_score(self, event_data: Dict[str, Any], 
                            intelligence: ThreatIntelligence) -> float:
        """Calculate risk score based on event and intelligence"""
        base_risk = intelligence.confidence * 0.5
        
        severity_multiplier = {
            'low': 0.3,
            'medium': 0.6,
            'high': 0.8,
            'critical': 1.0
        }.get(intelligence.severity.lower(), 0.5)
        
        event_risk = event_data.get('anomaly_score', 0.0) * 0.3
        
        risk_score = min(1.0, base_risk + (severity_multiplier * 0.4) + event_risk)
        return risk_score
    
    def _generate_recommendations(self, event_data: Dict[str, Any], 
                                intelligence: ThreatIntelligence) -> List[str]:
        """Generate recommendations based on threat intelligence"""
        recommendations = []
        
        if intelligence.intel_type == ThreatIntelType.IOC:
            recommendations.extend([
                "Block identified indicators of compromise",
                "Investigate related network traffic",
                "Check for additional IOCs on affected systems"
            ])
        
        if intelligence.intel_type == ThreatIntelType.TTP:
            recommendations.extend([
                "Review access controls and privilege escalation paths",
                "Monitor for similar tactics and techniques",
                "Implement additional detection rules"
            ])
        
        if event_data.get('severity') in ['high', 'critical']:
            recommendations.extend([
                "Initiate incident response procedures",
                "Isolate affected systems if necessary",
                "Preserve forensic evidence"
            ])
        
        return recommendations
    
    async def _store_security_insight(self, insight: SecurityInsight) -> None:
        """Store security insight in hAIveMind"""
        try:
            insight_data = {
                'insight_id': insight.insight_id,
                'title': insight.title,
                'description': insight.description,
                'insight_type': insight.insight_type,
                'confidence_score': insight.confidence_score,
                'risk_score': insight.risk_score,
                'affected_systems': insight.affected_systems,
                'related_events': insight.related_events,
                'related_intel': insight.related_intel,
                'recommendations': insight.recommendations,
                'created_at': insight.created_at.isoformat(),
                'created_by': insight.created_by,
                'machine_id': self.config.get('machine_id', 'unknown')
            }
            
            await self.memory_server.store_memory(
                content=json.dumps(insight_data),
                category='security',
                subcategory='threat_insight',
                tags=['insight', 'threat_correlation', 'vault_security'],
                importance=min(0.95, 0.5 + (insight.risk_score * 0.4))
            )
            
            self.security_insights[insight.insight_id] = insight
            
        except Exception as e:
            self.logger.error(f"Failed to store security insight: {str(e)}")
    
    async def _broadcast_security_discovery(self, event_data: Dict[str, Any], 
                                          insights: List[SecurityInsight]) -> None:
        """Broadcast security discovery to hAIveMind network"""
        try:
            max_risk_insight = max(insights, key=lambda i: i.risk_score)
            
            discovery_data = {
                'discovery_type': 'security_threat',
                'source_agent': 'vault_security_agent',
                'timestamp': datetime.utcnow().isoformat(),
                'severity': 'high' if max_risk_insight.risk_score > 0.8 else 'medium',
                'title': f"Vault Security Threat Detected: {max_risk_insight.title}",
                'description': max_risk_insight.description,
                'affected_systems': max_risk_insight.affected_systems,
                'indicators': self._extract_event_indicators(event_data),
                'recommendations': max_risk_insight.recommendations,
                'confidence': max_risk_insight.confidence_score,
                'risk_score': max_risk_insight.risk_score,
                'machine_id': self.config.get('machine_id', 'unknown')
            }
            
            await self.memory_server.broadcast_discovery(
                message=f"Critical vault security threat detected: {max_risk_insight.title}",
                category='security',
                severity='high' if max_risk_insight.risk_score > 0.8 else 'medium',
                data=discovery_data
            )
            
            self.logger.warning(f"Broadcasted security discovery: {max_risk_insight.title}")
            
        except Exception as e:
            self.logger.error(f"Failed to broadcast security discovery: {str(e)}")
    
    async def receive_threat_intelligence(self, intel_data: Dict[str, Any]) -> bool:
        """Receive and process threat intelligence from hAIveMind network"""
        try:
            intelligence = ThreatIntelligence(
                intel_id=intel_data.get('intel_id', secrets.token_hex(16)),
                intel_type=ThreatIntelType(intel_data['intel_type']),
                title=intel_data['title'],
                description=intel_data['description'],
                indicators=intel_data.get('indicators', []),
                confidence=intel_data.get('confidence', 0.5),
                severity=intel_data.get('severity', 'medium'),
                classification=IntelligenceClassification(intel_data.get('classification', 'tlp_green')),
                source=intel_data.get('source', 'haivemind_network'),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                expires_at=datetime.fromisoformat(intel_data['expires_at']) if intel_data.get('expires_at') else None,
                tags=intel_data.get('tags', []),
                mitre_tactics=intel_data.get('mitre_tactics', []),
                mitre_techniques=intel_data.get('mitre_techniques', [])
            )
            
            self.threat_intelligence[intelligence.intel_id] = intelligence
            await self._store_threat_intelligence(intelligence)
            
            self.logger.info(f"Received threat intelligence: {intelligence.title}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to process threat intelligence: {str(e)}")
            return False
    
    async def _store_threat_intelligence(self, intelligence: ThreatIntelligence) -> None:
        """Store threat intelligence in hAIveMind"""
        try:
            intel_data = {
                'intel_id': intelligence.intel_id,
                'intel_type': intelligence.intel_type.value,
                'title': intelligence.title,
                'description': intelligence.description,
                'indicators': intelligence.indicators,
                'confidence': intelligence.confidence,
                'severity': intelligence.severity,
                'classification': intelligence.classification.value,
                'source': intelligence.source,
                'created_at': intelligence.created_at.isoformat(),
                'updated_at': intelligence.updated_at.isoformat(),
                'expires_at': intelligence.expires_at.isoformat() if intelligence.expires_at else None,
                'tags': intelligence.tags,
                'mitre_tactics': intelligence.mitre_tactics,
                'mitre_techniques': intelligence.mitre_techniques,
                'machine_id': self.config.get('machine_id', 'unknown')
            }
            
            await self.memory_server.store_memory(
                content=json.dumps(intel_data),
                category='security',
                subcategory='threat_intelligence',
                tags=['threat_intel', intelligence.intel_type.value] + intelligence.tags,
                importance=min(0.9, intelligence.confidence)
            )
            
        except Exception as e:
            self.logger.error(f"Failed to store threat intelligence: {str(e)}")
    
    async def initiate_collaborative_response(self, threat_category: SecurityEventCategory,
                                            threat_description: str,
                                            affected_assets: List[str]) -> str:
        """Initiate collaborative response across hAIveMind network"""
        try:
            response_id = secrets.token_hex(16)
            
            # Query network for agents capable of responding to this threat
            capable_agents = await self._find_capable_agents(threat_category)
            
            response = CollaborativeResponse(
                response_id=response_id,
                threat_category=threat_category,
                threat_description=threat_description,
                affected_assets=affected_assets,
                response_actions=[],
                participating_agents=capable_agents,
                coordination_status='initiated',
                initiated_at=datetime.utcnow()
            )
            
            self.collaborative_responses[response_id] = response
            
            # Delegate tasks to capable agents
            await self._delegate_response_tasks(response)
            
            self.logger.info(f"Initiated collaborative response {response_id}")
            return response_id
            
        except Exception as e:
            self.logger.error(f"Failed to initiate collaborative response: {str(e)}")
            return ""
    
    async def _find_capable_agents(self, threat_category: SecurityEventCategory) -> List[str]:
        """Find agents capable of responding to specific threat category"""
        try:
            capability_map = {
                SecurityEventCategory.AUTHENTICATION_ANOMALY: ['authentication', 'access_control'],
                SecurityEventCategory.CREDENTIAL_COMPROMISE: ['credential_security', 'identity_management'],
                SecurityEventCategory.PRIVILEGE_ESCALATION: ['privilege_management', 'access_control'],
                SecurityEventCategory.DATA_EXFILTRATION: ['data_protection', 'network_monitoring'],
                SecurityEventCategory.LATERAL_MOVEMENT: ['network_security', 'endpoint_detection']
            }
            
            required_capabilities = capability_map.get(threat_category, ['general_security'])
            
            # Search hAIveMind for agents with required capabilities
            search_results = await self.memory_server.search_memories(
                query=f"agent capabilities {' '.join(required_capabilities)}",
                category='agent',
                limit=50
            )
            
            capable_agents = []
            for memory in search_results.get('memories', []):
                try:
                    agent_data = json.loads(memory['content'])
                    agent_capabilities = agent_data.get('capabilities', [])
                    
                    if any(cap in agent_capabilities for cap in required_capabilities):
                        capable_agents.append(agent_data.get('agent_id', 'unknown'))
                        
                except Exception as e:
                    continue
            
            return capable_agents
            
        except Exception as e:
            self.logger.error(f"Failed to find capable agents: {str(e)}")
            return []
    
    async def _delegate_response_tasks(self, response: CollaborativeResponse) -> None:
        """Delegate response tasks to participating agents"""
        try:
            task_template = {
                'response_id': response.response_id,
                'threat_category': response.threat_category.value,
                'threat_description': response.threat_description,
                'affected_assets': response.affected_assets,
                'priority': 'high' if response.threat_category in [
                    SecurityEventCategory.CREDENTIAL_COMPROMISE,
                    SecurityEventCategory.DATA_EXFILTRATION
                ] else 'medium'
            }
            
            for agent_id in response.participating_agents:
                task_data = task_template.copy()
                task_data['assigned_agent'] = agent_id
                task_data['task_id'] = secrets.token_hex(8)
                
                await self.memory_server.delegate_task(
                    task_description=f"Respond to security threat: {response.threat_description}",
                    assigned_agent=agent_id,
                    priority=task_data['priority'],
                    context=task_data
                )
            
        except Exception as e:
            self.logger.error(f"Failed to delegate response tasks: {str(e)}")
    
    async def _threat_intelligence_updater(self) -> None:
        """Background task to update threat intelligence"""
        while True:
            try:
                # Query hAIveMind network for new threat intelligence
                recent_intel = await self.memory_server.search_memories(
                    query="threat intelligence recent",
                    category="security",
                    limit=100
                )
                
                for memory in recent_intel.get('memories', []):
                    if 'threat_intelligence' in memory.get('tags', []):
                        try:
                            intel_data = json.loads(memory['content'])
                            if intel_data.get('intel_id') not in self.threat_intelligence:
                                await self.receive_threat_intelligence(intel_data)
                        except Exception as e:
                            continue
                
                # Clean up expired intelligence
                await self._cleanup_expired_intelligence()
                
                await asyncio.sleep(1800)  # Update every 30 minutes
                
            except Exception as e:
                self.logger.error(f"Threat intelligence updater error: {str(e)}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _cleanup_expired_intelligence(self) -> None:
        """Clean up expired threat intelligence"""
        current_time = datetime.utcnow()
        expired_intel = []
        
        for intel_id, intel in self.threat_intelligence.items():
            if intel.expires_at and current_time > intel.expires_at:
                expired_intel.append(intel_id)
        
        for intel_id in expired_intel:
            del self.threat_intelligence[intel_id]
            self.logger.debug(f"Removed expired intelligence: {intel_id}")
    
    async def _collaborative_analysis(self) -> None:
        """Background task for collaborative security analysis"""
        while True:
            try:
                # Analyze patterns across hAIveMind network
                network_patterns = await self._analyze_network_security_patterns()
                
                if network_patterns:
                    await self._generate_collaborative_insights(network_patterns)
                
                await asyncio.sleep(3600)  # Analyze every hour
                
            except Exception as e:
                self.logger.error(f"Collaborative analysis error: {str(e)}")
                await asyncio.sleep(600)
    
    async def _analyze_network_security_patterns(self) -> Dict[str, Any]:
        """Analyze security patterns across the hAIveMind network"""
        try:
            # Get recent security events from across the network
            network_events = await self.memory_server.search_memories(
                query="security event anomaly threat",
                category="security",
                limit=1000
            )
            
            patterns = {
                'common_threats': {},
                'trending_indicators': {},
                'attack_patterns': {},
                'geographic_clusters': {}
            }
            
            # Analyze patterns (simplified implementation)
            for memory in network_events.get('memories', []):
                try:
                    event_data = json.loads(memory['content'])
                    
                    # Count threat types
                    threat_type = event_data.get('event_type', 'unknown')
                    patterns['common_threats'][threat_type] = patterns['common_threats'].get(threat_type, 0) + 1
                    
                    # Track indicators
                    source_ip = event_data.get('source_ip')
                    if source_ip:
                        patterns['trending_indicators'][source_ip] = patterns['trending_indicators'].get(source_ip, 0) + 1
                
                except Exception as e:
                    continue
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Failed to analyze network patterns: {str(e)}")
            return {}
    
    async def _generate_collaborative_insights(self, patterns: Dict[str, Any]) -> None:
        """Generate insights from collaborative network analysis"""
        try:
            insights = []
            
            # Generate insights based on common threats
            common_threats = patterns.get('common_threats', {})
            if common_threats:
                top_threat = max(common_threats.items(), key=lambda x: x[1])
                
                insight = SecurityInsight(
                    insight_id=secrets.token_hex(16),
                    title=f"Network-wide threat trend: {top_threat[0]}",
                    description=f"Detected {top_threat[1]} instances of {top_threat[0]} across hAIveMind network",
                    insight_type="network_trend",
                    confidence_score=0.8,
                    risk_score=min(0.9, top_threat[1] / 100.0),
                    affected_systems=["network_wide"],
                    related_events=[],
                    related_intel=[],
                    recommendations=[
                        "Review defensive measures against this threat type",
                        "Share countermeasures with network participants",
                        "Monitor for escalation patterns"
                    ],
                    created_at=datetime.utcnow(),
                    created_by='collaborative_analysis'
                )
                
                await self._store_security_insight(insight)
                
                # Share insight with network
                await self.memory_server.broadcast_discovery(
                    message=f"Network trend analysis: {insight.title}",
                    category='security',
                    severity='medium',
                    data={
                        'insight_type': 'network_trend',
                        'threat_type': top_threat[0],
                        'instance_count': top_threat[1],
                        'recommendations': insight.recommendations
                    }
                )
            
        except Exception as e:
            self.logger.error(f"Failed to generate collaborative insights: {str(e)}")
    
    async def _intelligence_sharing(self) -> None:
        """Background task for sharing intelligence with network"""
        while True:
            try:
                # Share high-confidence, low-classification intelligence
                shareable_intel = [
                    intel for intel in self.threat_intelligence.values()
                    if (intel.confidence > 0.7 and 
                        intel.classification in [IntelligenceClassification.TLP_WHITE, IntelligenceClassification.TLP_GREEN])
                ]
                
                for intel in shareable_intel:
                    sharing_data = {
                        'intel_id': intel.intel_id,
                        'intel_type': intel.intel_type.value,
                        'title': intel.title,
                        'description': intel.description,
                        'indicators': intel.indicators,
                        'confidence': intel.confidence,
                        'severity': intel.severity,
                        'classification': intel.classification.value,
                        'source': 'vault_security_agent',
                        'shared_at': datetime.utcnow().isoformat()
                    }
                    
                    await self.memory_server.broadcast_discovery(
                        message=f"Sharing threat intelligence: {intel.title}",
                        category='security',
                        severity=intel.severity,
                        data=sharing_data
                    )
                
                await asyncio.sleep(7200)  # Share every 2 hours
                
            except Exception as e:
                self.logger.error(f"Intelligence sharing error: {str(e)}")
                await asyncio.sleep(600)
    
    async def get_haivemind_status(self) -> Dict[str, Any]:
        """Get hAIveMind integration status"""
        try:
            status = {
                'agent_registered': True,
                'threat_intelligence_count': len(self.threat_intelligence),
                'security_insights_count': len(self.security_insights),
                'collaborative_responses_active': len([
                    r for r in self.collaborative_responses.values() 
                    if r.coordination_status in ['initiated', 'in_progress']
                ]),
                'intelligence_feeds': len(self.intelligence_feeds),
                'network_connectivity': 'active',
                'last_intelligence_update': datetime.utcnow().isoformat(),
                'capabilities': [
                    'threat_correlation',
                    'collaborative_response',
                    'intelligence_sharing',
                    'pattern_analysis'
                ]
            }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get hAIveMind status: {str(e)}")
            return {'error': str(e)}