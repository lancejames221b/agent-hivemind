"""
SIEM Integration for Security Monitoring
Integrates with popular SIEM systems for comprehensive security monitoring.

Author: Lance James, Unit 221B
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import secrets
import aiohttp
import hashlib
import xml.etree.ElementTree as ET
import redis


class SIEMProvider(Enum):
    """Supported SIEM providers"""
    SPLUNK = "splunk"
    QRADAR = "qradar"
    ARCSIGHT = "arcsight"
    ELASTIC_SIEM = "elastic_siem"
    AZURE_SENTINEL = "azure_sentinel"
    SUMO_LOGIC = "sumo_logic"
    DATADOG = "datadog"
    CHRONICLE = "chronicle"
    PHANTOM = "phantom"
    DEMISTO = "demisto"


class EventSeverity(Enum):
    """Event severity levels for SIEM"""
    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventType(Enum):
    """Types of security events"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    ACCESS_VIOLATION = "access_violation"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    ANOMALY_DETECTED = "anomaly_detected"
    COMPLIANCE_VIOLATION = "compliance_violation"
    SYSTEM_COMPROMISE = "system_compromise"
    CREDENTIAL_COMPROMISE = "credential_compromise"
    MALICIOUS_ACTIVITY = "malicious_activity"


@dataclass
class SIEMConfiguration:
    """Configuration for SIEM provider"""
    provider: SIEMProvider
    endpoint: str
    api_key: str
    organization_id: Optional[str] = None
    index_name: Optional[str] = None
    source_type: Optional[str] = None
    verify_ssl: bool = True
    timeout: int = 30
    batch_size: int = 100
    retry_count: int = 3
    custom_headers: Dict[str, str] = field(default_factory=dict)
    custom_fields: Dict[str, str] = field(default_factory=dict)


@dataclass
class SecurityEvent:
    """Security event for SIEM forwarding"""
    event_id: str
    timestamp: datetime
    event_type: EventType
    severity: EventSeverity
    source_system: str
    user_id: Optional[str]
    credential_id: Optional[str]
    source_ip: str
    destination_ip: Optional[str]
    user_agent: Optional[str]
    action: str
    result: str
    message: str
    raw_data: Dict[str, Any]
    tags: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SIEMAlert:
    """Alert from SIEM system"""
    alert_id: str
    siem_provider: SIEMProvider
    alert_name: str
    severity: EventSeverity
    created_time: datetime
    description: str
    affected_assets: List[str]
    indicators: List[Dict[str, Any]]
    raw_alert: Dict[str, Any]


class SIEMIntegration:
    """SIEM integration for security monitoring"""
    
    def __init__(self, config: Dict[str, Any], redis_client: redis.Redis):
        self.config = config
        self.redis = redis_client
        self.logger = logging.getLogger(__name__)
        self.siem_configs: Dict[str, SIEMConfiguration] = {}
        self.event_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
        self.batch_processors: Dict[str, asyncio.Task] = {}
        self.alert_handlers: Dict[SIEMProvider, callable] = {}
        self.field_mappings: Dict[SIEMProvider, Dict[str, str]] = {}
        
    async def initialize_siem_integrations(self) -> bool:
        """Initialize SIEM integrations from configuration"""
        try:
            siem_config = self.config.get('vault', {}).get('siem_integration', {})
            
            for provider_name, provider_config in siem_config.items():
                try:
                    siem_config_obj = SIEMConfiguration(
                        provider=SIEMProvider(provider_config['provider']),
                        endpoint=provider_config['endpoint'],
                        api_key=provider_config['api_key'],
                        organization_id=provider_config.get('organization_id'),
                        index_name=provider_config.get('index_name'),
                        source_type=provider_config.get('source_type'),
                        verify_ssl=provider_config.get('verify_ssl', True),
                        timeout=provider_config.get('timeout', 30),
                        batch_size=provider_config.get('batch_size', 100),
                        retry_count=provider_config.get('retry_count', 3),
                        custom_headers=provider_config.get('custom_headers', {}),
                        custom_fields=provider_config.get('custom_fields', {})
                    )
                    
                    if await self._test_siem_connection(siem_config_obj):
                        self.siem_configs[provider_name] = siem_config_obj
                        await self._initialize_field_mappings(siem_config_obj.provider)
                        await self._start_batch_processor(provider_name)
                        self.logger.info(f"SIEM provider {provider_name} initialized successfully")
                    else:
                        self.logger.error(f"Failed to connect to SIEM provider {provider_name}")
                        
                except Exception as e:
                    self.logger.error(f"Failed to initialize SIEM provider {provider_name}: {str(e)}")
            
            await self._initialize_alert_handlers()
            asyncio.create_task(self._event_forwarder())
            
            self.logger.info(f"Initialized {len(self.siem_configs)} SIEM integrations")
            return len(self.siem_configs) > 0
            
        except Exception as e:
            self.logger.error(f"Failed to initialize SIEM integrations: {str(e)}")
            return False
    
    async def _test_siem_connection(self, siem_config: SIEMConfiguration) -> bool:
        """Test connection to SIEM provider"""
        try:
            if siem_config.provider == SIEMProvider.SPLUNK:
                return await self._test_splunk_connection(siem_config)
            elif siem_config.provider == SIEMProvider.QRADAR:
                return await self._test_qradar_connection(siem_config)
            elif siem_config.provider == SIEMProvider.ELASTIC_SIEM:
                return await self._test_elastic_connection(siem_config)
            elif siem_config.provider == SIEMProvider.AZURE_SENTINEL:
                return await self._test_azure_sentinel_connection(siem_config)
            elif siem_config.provider == SIEMProvider.SUMO_LOGIC:
                return await self._test_sumo_logic_connection(siem_config)
            else:
                return await self._test_generic_siem_connection(siem_config)
                
        except Exception as e:
            self.logger.error(f"SIEM connection test failed: {str(e)}")
            return False
    
    async def _test_splunk_connection(self, siem_config: SIEMConfiguration) -> bool:
        """Test Splunk connection"""
        try:
            headers = {
                'Authorization': f'Splunk {siem_config.api_key}',
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{siem_config.endpoint}/services/server/info",
                    headers=headers,
                    ssl=siem_config.verify_ssl,
                    timeout=aiohttp.ClientTimeout(total=siem_config.timeout)
                ) as response:
                    return response.status == 200
                    
        except Exception:
            return False
    
    async def _test_qradar_connection(self, siem_config: SIEMConfiguration) -> bool:
        """Test QRadar connection"""
        try:
            headers = {
                'SEC': siem_config.api_key,
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{siem_config.endpoint}/api/system/about",
                    headers=headers,
                    ssl=siem_config.verify_ssl,
                    timeout=aiohttp.ClientTimeout(total=siem_config.timeout)
                ) as response:
                    return response.status == 200
                    
        except Exception:
            return False
    
    async def _test_elastic_connection(self, siem_config: SIEMConfiguration) -> bool:
        """Test Elasticsearch/Elastic SIEM connection"""
        try:
            headers = {
                'Authorization': f'ApiKey {siem_config.api_key}',
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{siem_config.endpoint}/_cluster/health",
                    headers=headers,
                    ssl=siem_config.verify_ssl,
                    timeout=aiohttp.ClientTimeout(total=siem_config.timeout)
                ) as response:
                    return response.status == 200
                    
        except Exception:
            return False
    
    async def _test_azure_sentinel_connection(self, siem_config: SIEMConfiguration) -> bool:
        """Test Azure Sentinel connection"""
        try:
            headers = {
                'Authorization': f'Bearer {siem_config.api_key}',
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{siem_config.endpoint}/subscriptions/{siem_config.organization_id}/providers/Microsoft.SecurityInsights/alertRules",
                    headers=headers,
                    ssl=siem_config.verify_ssl,
                    timeout=aiohttp.ClientTimeout(total=siem_config.timeout)
                ) as response:
                    return response.status == 200
                    
        except Exception:
            return False
    
    async def _test_sumo_logic_connection(self, siem_config: SIEMConfiguration) -> bool:
        """Test Sumo Logic connection"""
        try:
            headers = {
                'Authorization': f'Basic {siem_config.api_key}',
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{siem_config.endpoint}/api/v1/collectors",
                    headers=headers,
                    ssl=siem_config.verify_ssl,
                    timeout=aiohttp.ClientTimeout(total=siem_config.timeout)
                ) as response:
                    return response.status == 200
                    
        except Exception:
            return False
    
    async def _test_generic_siem_connection(self, siem_config: SIEMConfiguration) -> bool:
        """Test generic SIEM connection"""
        try:
            headers = {
                'Authorization': f'Bearer {siem_config.api_key}',
                'Content-Type': 'application/json'
            }
            headers.update(siem_config.custom_headers)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{siem_config.endpoint}/health",
                    headers=headers,
                    ssl=siem_config.verify_ssl,
                    timeout=aiohttp.ClientTimeout(total=siem_config.timeout)
                ) as response:
                    return response.status == 200
                    
        except Exception:
            return False
    
    async def _initialize_field_mappings(self, provider: SIEMProvider) -> None:
        """Initialize field mappings for SIEM provider"""
        if provider == SIEMProvider.SPLUNK:
            self.field_mappings[provider] = {
                'timestamp': '_time',
                'event_id': 'event_id',
                'event_type': 'event_type',
                'severity': 'severity',
                'source_system': 'source',
                'user_id': 'user',
                'source_ip': 'src_ip',
                'action': 'action',
                'result': 'result',
                'message': 'message'
            }
        elif provider == SIEMProvider.QRADAR:
            self.field_mappings[provider] = {
                'timestamp': 'StartTime',
                'event_id': 'EventID',
                'event_type': 'EventCategory',
                'severity': 'Severity',
                'source_system': 'SourceIP',
                'user_id': 'Username',
                'source_ip': 'SourceIP',
                'action': 'EventName',
                'result': 'EventOutcome',
                'message': 'Message'
            }
        elif provider == SIEMProvider.ELASTIC_SIEM:
            self.field_mappings[provider] = {
                'timestamp': '@timestamp',
                'event_id': 'event.id',
                'event_type': 'event.type',
                'severity': 'event.severity',
                'source_system': 'observer.name',
                'user_id': 'user.name',
                'source_ip': 'source.ip',
                'action': 'event.action',
                'result': 'event.outcome',
                'message': 'message'
            }
        else:
            self.field_mappings[provider] = {
                'timestamp': 'timestamp',
                'event_id': 'event_id',
                'event_type': 'event_type',
                'severity': 'severity',
                'source_system': 'source_system',
                'user_id': 'user_id',
                'source_ip': 'source_ip',
                'action': 'action',
                'result': 'result',
                'message': 'message'
            }
    
    async def _start_batch_processor(self, provider_name: str) -> None:
        """Start batch processor for SIEM provider"""
        task = asyncio.create_task(self._batch_processor(provider_name))
        self.batch_processors[provider_name] = task
    
    async def _batch_processor(self, provider_name: str) -> None:
        """Batch processor for SIEM events"""
        siem_config = self.siem_configs[provider_name]
        event_batch = []
        
        while True:
            try:
                try:
                    event = await asyncio.wait_for(self.event_queue.get(), timeout=30)
                    event_batch.append(event)
                    
                    if len(event_batch) >= siem_config.batch_size:
                        await self._send_events_to_siem(provider_name, event_batch)
                        event_batch = []
                        
                except asyncio.TimeoutError:
                    if event_batch:
                        await self._send_events_to_siem(provider_name, event_batch)
                        event_batch = []
                        
            except Exception as e:
                self.logger.error(f"Batch processor error for {provider_name}: {str(e)}")
                await asyncio.sleep(5)
    
    async def _event_forwarder(self) -> None:
        """Forward events to all configured SIEM systems"""
        while True:
            try:
                await asyncio.sleep(1)
                
                event_keys = await self.redis.lrange("vault_security_events", 0, 999)
                if not event_keys:
                    continue
                
                for event_data in event_keys:
                    try:
                        event_json = json.loads(event_data.decode() if isinstance(event_data, bytes) else event_data)
                        security_event = SecurityEvent(
                            event_id=event_json['event_id'],
                            timestamp=datetime.fromisoformat(event_json['timestamp']),
                            event_type=EventType(event_json['event_type']),
                            severity=EventSeverity(event_json['severity']),
                            source_system=event_json['source_system'],
                            user_id=event_json.get('user_id'),
                            credential_id=event_json.get('credential_id'),
                            source_ip=event_json['source_ip'],
                            destination_ip=event_json.get('destination_ip'),
                            user_agent=event_json.get('user_agent'),
                            action=event_json['action'],
                            result=event_json['result'],
                            message=event_json['message'],
                            raw_data=event_json.get('raw_data', {}),
                            tags=event_json.get('tags', []),
                            custom_fields=event_json.get('custom_fields', {})
                        )
                        
                        await self.event_queue.put(security_event)
                        
                    except Exception as e:
                        self.logger.error(f"Failed to parse event: {str(e)}")
                
                await self.redis.ltrim("vault_security_events", len(event_keys), -1)
                
            except Exception as e:
                self.logger.error(f"Event forwarder error: {str(e)}")
                await asyncio.sleep(5)
    
    async def _send_events_to_siem(self, provider_name: str, events: List[SecurityEvent]) -> bool:
        """Send events to specific SIEM provider"""
        try:
            siem_config = self.siem_configs[provider_name]
            
            if siem_config.provider == SIEMProvider.SPLUNK:
                return await self._send_to_splunk(siem_config, events)
            elif siem_config.provider == SIEMProvider.QRADAR:
                return await self._send_to_qradar(siem_config, events)
            elif siem_config.provider == SIEMProvider.ELASTIC_SIEM:
                return await self._send_to_elastic(siem_config, events)
            elif siem_config.provider == SIEMProvider.AZURE_SENTINEL:
                return await self._send_to_azure_sentinel(siem_config, events)
            elif siem_config.provider == SIEMProvider.SUMO_LOGIC:
                return await self._send_to_sumo_logic(siem_config, events)
            else:
                return await self._send_to_generic_siem(siem_config, events)
                
        except Exception as e:
            self.logger.error(f"Failed to send events to {provider_name}: {str(e)}")
            return False
    
    async def _send_to_splunk(self, siem_config: SIEMConfiguration, events: List[SecurityEvent]) -> bool:
        """Send events to Splunk"""
        try:
            headers = {
                'Authorization': f'Splunk {siem_config.api_key}',
                'Content-Type': 'application/json'
            }
            
            splunk_events = []
            field_mapping = self.field_mappings[SIEMProvider.SPLUNK]
            
            for event in events:
                splunk_event = {
                    'time': event.timestamp.timestamp(),
                    'sourcetype': siem_config.source_type or 'vault_security',
                    'index': siem_config.index_name or 'main',
                    'event': self._map_event_fields(event, field_mapping)
                }
                splunk_events.append(splunk_event)
            
            payload = '\n'.join([json.dumps(event) for event in splunk_events])
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{siem_config.endpoint}/services/collector/event",
                    data=payload,
                    headers=headers,
                    ssl=siem_config.verify_ssl,
                    timeout=aiohttp.ClientTimeout(total=siem_config.timeout)
                ) as response:
                    success = response.status == 200
                    if success:
                        self.logger.debug(f"Sent {len(events)} events to Splunk")
                    else:
                        self.logger.error(f"Splunk API error: {response.status} - {await response.text()}")
                    return success
                    
        except Exception as e:
            self.logger.error(f"Failed to send to Splunk: {str(e)}")
            return False
    
    async def _send_to_qradar(self, siem_config: SIEMConfiguration, events: List[SecurityEvent]) -> bool:
        """Send events to IBM QRadar"""
        try:
            headers = {
                'SEC': siem_config.api_key,
                'Content-Type': 'application/json'
            }
            
            qradar_events = []
            field_mapping = self.field_mappings[SIEMProvider.QRADAR]
            
            for event in events:
                qradar_event = self._map_event_fields(event, field_mapping)
                qradar_events.append(qradar_event)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{siem_config.endpoint}/api/siem/events",
                    json=qradar_events,
                    headers=headers,
                    ssl=siem_config.verify_ssl,
                    timeout=aiohttp.ClientTimeout(total=siem_config.timeout)
                ) as response:
                    success = response.status in [200, 201]
                    if success:
                        self.logger.debug(f"Sent {len(events)} events to QRadar")
                    else:
                        self.logger.error(f"QRadar API error: {response.status} - {await response.text()}")
                    return success
                    
        except Exception as e:
            self.logger.error(f"Failed to send to QRadar: {str(e)}")
            return False
    
    async def _send_to_elastic(self, siem_config: SIEMConfiguration, events: List[SecurityEvent]) -> bool:
        """Send events to Elasticsearch/Elastic SIEM"""
        try:
            headers = {
                'Authorization': f'ApiKey {siem_config.api_key}',
                'Content-Type': 'application/x-ndjson'
            }
            
            field_mapping = self.field_mappings[SIEMProvider.ELASTIC_SIEM]
            bulk_data = []
            
            for event in events:
                index_action = {
                    "index": {
                        "_index": siem_config.index_name or f"vault-security-{datetime.utcnow().strftime('%Y.%m.%d')}"
                    }
                }
                event_doc = self._map_event_fields(event, field_mapping)
                
                bulk_data.append(json.dumps(index_action))
                bulk_data.append(json.dumps(event_doc))
            
            payload = '\n'.join(bulk_data) + '\n'
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{siem_config.endpoint}/_bulk",
                    data=payload,
                    headers=headers,
                    ssl=siem_config.verify_ssl,
                    timeout=aiohttp.ClientTimeout(total=siem_config.timeout)
                ) as response:
                    success = response.status == 200
                    if success:
                        result = await response.json()
                        if result.get('errors'):
                            self.logger.warning(f"Some events failed to index in Elasticsearch")
                        self.logger.debug(f"Sent {len(events)} events to Elasticsearch")
                    else:
                        self.logger.error(f"Elasticsearch API error: {response.status} - {await response.text()}")
                    return success
                    
        except Exception as e:
            self.logger.error(f"Failed to send to Elasticsearch: {str(e)}")
            return False
    
    async def _send_to_azure_sentinel(self, siem_config: SIEMConfiguration, events: List[SecurityEvent]) -> bool:
        """Send events to Azure Sentinel"""
        try:
            headers = {
                'Authorization': f'Bearer {siem_config.api_key}',
                'Content-Type': 'application/json',
                'Log-Type': 'VaultSecurity'
            }
            
            azure_events = []
            for event in events:
                azure_event = {
                    'TimeGenerated': event.timestamp.isoformat(),
                    'EventId': event.event_id,
                    'EventType': event.event_type.value,
                    'Severity': event.severity.value,
                    'SourceSystem': event.source_system,
                    'UserId': event.user_id,
                    'CredentialId': event.credential_id,
                    'SourceIP': event.source_ip,
                    'UserAgent': event.user_agent,
                    'Action': event.action,
                    'Result': event.result,
                    'Message': event.message,
                    'RawData': json.dumps(event.raw_data),
                    'Tags': ','.join(event.tags)
                }
                azure_events.append(azure_event)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{siem_config.endpoint}/api/logs",
                    json=azure_events,
                    headers=headers,
                    ssl=siem_config.verify_ssl,
                    timeout=aiohttp.ClientTimeout(total=siem_config.timeout)
                ) as response:
                    success = response.status == 200
                    if success:
                        self.logger.debug(f"Sent {len(events)} events to Azure Sentinel")
                    else:
                        self.logger.error(f"Azure Sentinel API error: {response.status} - {await response.text()}")
                    return success
                    
        except Exception as e:
            self.logger.error(f"Failed to send to Azure Sentinel: {str(e)}")
            return False
    
    async def _send_to_sumo_logic(self, siem_config: SIEMConfiguration, events: List[SecurityEvent]) -> bool:
        """Send events to Sumo Logic"""
        try:
            headers = {
                'Authorization': f'Basic {siem_config.api_key}',
                'Content-Type': 'application/json'
            }
            
            sumo_events = []
            for event in events:
                sumo_event = {
                    'timestamp': event.timestamp.isoformat(),
                    'event_id': event.event_id,
                    'event_type': event.event_type.value,
                    'severity': event.severity.value,
                    'source_system': event.source_system,
                    'user_id': event.user_id,
                    'credential_id': event.credential_id,
                    'source_ip': event.source_ip,
                    'action': event.action,
                    'result': event.result,
                    'message': event.message,
                    'raw_data': event.raw_data,
                    'tags': event.tags
                }
                sumo_events.append(sumo_event)
            
            payload = '\n'.join([json.dumps(event) for event in sumo_events])
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{siem_config.endpoint}/api/v1/collectors/{siem_config.organization_id}/sources",
                    data=payload,
                    headers=headers,
                    ssl=siem_config.verify_ssl,
                    timeout=aiohttp.ClientTimeout(total=siem_config.timeout)
                ) as response:
                    success = response.status == 200
                    if success:
                        self.logger.debug(f"Sent {len(events)} events to Sumo Logic")
                    else:
                        self.logger.error(f"Sumo Logic API error: {response.status} - {await response.text()}")
                    return success
                    
        except Exception as e:
            self.logger.error(f"Failed to send to Sumo Logic: {str(e)}")
            return False
    
    async def _send_to_generic_siem(self, siem_config: SIEMConfiguration, events: List[SecurityEvent]) -> bool:
        """Send events to generic SIEM"""
        try:
            headers = {
                'Authorization': f'Bearer {siem_config.api_key}',
                'Content-Type': 'application/json'
            }
            headers.update(siem_config.custom_headers)
            
            generic_events = []
            for event in events:
                generic_event = {
                    'timestamp': event.timestamp.isoformat(),
                    'event_id': event.event_id,
                    'event_type': event.event_type.value,
                    'severity': event.severity.value,
                    'source_system': event.source_system,
                    'user_id': event.user_id,
                    'credential_id': event.credential_id,
                    'source_ip': event.source_ip,
                    'action': event.action,
                    'result': event.result,
                    'message': event.message,
                    'raw_data': event.raw_data
                }
                generic_event.update(siem_config.custom_fields)
                generic_events.append(generic_event)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{siem_config.endpoint}/events",
                    json=generic_events,
                    headers=headers,
                    ssl=siem_config.verify_ssl,
                    timeout=aiohttp.ClientTimeout(total=siem_config.timeout)
                ) as response:
                    success = response.status in [200, 201]
                    if success:
                        self.logger.debug(f"Sent {len(events)} events to generic SIEM")
                    else:
                        self.logger.error(f"Generic SIEM API error: {response.status} - {await response.text()}")
                    return success
                    
        except Exception as e:
            self.logger.error(f"Failed to send to generic SIEM: {str(e)}")
            return False
    
    def _map_event_fields(self, event: SecurityEvent, field_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Map event fields to SIEM-specific field names"""
        mapped_event = {}
        
        event_dict = {
            'timestamp': event.timestamp.isoformat(),
            'event_id': event.event_id,
            'event_type': event.event_type.value,
            'severity': event.severity.value,
            'source_system': event.source_system,
            'user_id': event.user_id,
            'credential_id': event.credential_id,
            'source_ip': event.source_ip,
            'destination_ip': event.destination_ip,
            'user_agent': event.user_agent,
            'action': event.action,
            'result': event.result,
            'message': event.message,
            'tags': ','.join(event.tags) if event.tags else '',
        }
        
        for field, value in event_dict.items():
            if value is not None:
                mapped_field = field_mapping.get(field, field)
                mapped_event[mapped_field] = value
        
        mapped_event.update(event.raw_data)
        mapped_event.update(event.custom_fields)
        
        return mapped_event
    
    async def send_security_event(self, event: SecurityEvent) -> bool:
        """Send security event to all configured SIEM systems"""
        try:
            event_data = {
                'event_id': event.event_id,
                'timestamp': event.timestamp.isoformat(),
                'event_type': event.event_type.value,
                'severity': event.severity.value,
                'source_system': event.source_system,
                'user_id': event.user_id,
                'credential_id': event.credential_id,
                'source_ip': event.source_ip,
                'destination_ip': event.destination_ip,
                'user_agent': event.user_agent,
                'action': event.action,
                'result': event.result,
                'message': event.message,
                'raw_data': event.raw_data,
                'tags': event.tags,
                'custom_fields': event.custom_fields
            }
            
            await self.redis.lpush("vault_security_events", json.dumps(event_data))
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to queue security event: {str(e)}")
            return False
    
    async def _initialize_alert_handlers(self) -> None:
        """Initialize SIEM alert handlers"""
        self.alert_handlers = {
            SIEMProvider.SPLUNK: self._handle_splunk_alerts,
            SIEMProvider.QRADAR: self._handle_qradar_alerts,
            SIEMProvider.ELASTIC_SIEM: self._handle_elastic_alerts,
            SIEMProvider.AZURE_SENTINEL: self._handle_azure_sentinel_alerts,
        }
        
        asyncio.create_task(self._alert_polling())
    
    async def _alert_polling(self) -> None:
        """Poll SIEM systems for new alerts"""
        while True:
            try:
                for provider_name, siem_config in self.siem_configs.items():
                    if siem_config.provider in self.alert_handlers:
                        handler = self.alert_handlers[siem_config.provider]
                        await handler(siem_config)
                
                await asyncio.sleep(300)  # Poll every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Alert polling error: {str(e)}")
                await asyncio.sleep(60)
    
    async def _handle_splunk_alerts(self, siem_config: SIEMConfiguration) -> None:
        """Handle alerts from Splunk"""
        try:
            headers = {
                'Authorization': f'Splunk {siem_config.api_key}',
                'Content-Type': 'application/json'
            }
            
            search_query = 'search source="vault_security" severity="high" OR severity="critical" | head 100'
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{siem_config.endpoint}/services/search/jobs",
                    data={'search': search_query},
                    headers=headers,
                    ssl=siem_config.verify_ssl
                ) as response:
                    if response.status == 201:
                        result = await response.text()
                        job_id = result.split('<sid>')[1].split('</sid>')[0]
                        await self._process_splunk_search_results(siem_config, job_id)
                        
        except Exception as e:
            self.logger.error(f"Failed to handle Splunk alerts: {str(e)}")
    
    async def _process_splunk_search_results(self, siem_config: SIEMConfiguration, job_id: str) -> None:
        """Process Splunk search results"""
        try:
            await asyncio.sleep(5)  # Wait for search to complete
            
            headers = {
                'Authorization': f'Splunk {siem_config.api_key}',
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{siem_config.endpoint}/services/search/jobs/{job_id}/results",
                    headers=headers,
                    ssl=siem_config.verify_ssl
                ) as response:
                    if response.status == 200:
                        results = await response.json()
                        for result in results.get('results', []):
                            await self._process_alert_result('splunk', result)
                            
        except Exception as e:
            self.logger.error(f"Failed to process Splunk search results: {str(e)}")
    
    async def _handle_qradar_alerts(self, siem_config: SIEMConfiguration) -> None:
        """Handle alerts from QRadar"""
        try:
            headers = {
                'SEC': siem_config.api_key,
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{siem_config.endpoint}/api/siem/offenses",
                    headers=headers,
                    ssl=siem_config.verify_ssl
                ) as response:
                    if response.status == 200:
                        offenses = await response.json()
                        for offense in offenses:
                            await self._process_alert_result('qradar', offense)
                            
        except Exception as e:
            self.logger.error(f"Failed to handle QRadar alerts: {str(e)}")
    
    async def _handle_elastic_alerts(self, siem_config: SIEMConfiguration) -> None:
        """Handle alerts from Elastic SIEM"""
        try:
            headers = {
                'Authorization': f'ApiKey {siem_config.api_key}',
                'Content-Type': 'application/json'
            }
            
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"event.severity": "high"}},
                            {"range": {"@timestamp": {"gte": "now-5m"}}}
                        ]
                    }
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{siem_config.endpoint}/{siem_config.index_name}/_search",
                    json=query,
                    headers=headers,
                    ssl=siem_config.verify_ssl
                ) as response:
                    if response.status == 200:
                        results = await response.json()
                        for hit in results.get('hits', {}).get('hits', []):
                            await self._process_alert_result('elastic', hit['_source'])
                            
        except Exception as e:
            self.logger.error(f"Failed to handle Elastic alerts: {str(e)}")
    
    async def _handle_azure_sentinel_alerts(self, siem_config: SIEMConfiguration) -> None:
        """Handle alerts from Azure Sentinel"""
        try:
            headers = {
                'Authorization': f'Bearer {siem_config.api_key}',
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{siem_config.endpoint}/subscriptions/{siem_config.organization_id}/providers/Microsoft.SecurityInsights/incidents",
                    headers=headers,
                    ssl=siem_config.verify_ssl
                ) as response:
                    if response.status == 200:
                        incidents = await response.json()
                        for incident in incidents.get('value', []):
                            await self._process_alert_result('azure_sentinel', incident)
                            
        except Exception as e:
            self.logger.error(f"Failed to handle Azure Sentinel alerts: {str(e)}")
    
    async def _process_alert_result(self, source: str, alert_data: Dict[str, Any]) -> None:
        """Process SIEM alert and take action"""
        try:
            alert_id = alert_data.get('id') or alert_data.get('_id') or secrets.token_hex(8)
            
            siem_alert = SIEMAlert(
                alert_id=alert_id,
                siem_provider=SIEMProvider(source),
                alert_name=alert_data.get('name') or alert_data.get('title', 'Unknown Alert'),
                severity=EventSeverity.HIGH,  # Default to high
                created_time=datetime.utcnow(),
                description=alert_data.get('description') or alert_data.get('message', ''),
                affected_assets=[],
                indicators=[],
                raw_alert=alert_data
            )
            
            await self._store_siem_alert(siem_alert)
            await self._respond_to_alert(siem_alert)
            
        except Exception as e:
            self.logger.error(f"Failed to process alert result: {str(e)}")
    
    async def _store_siem_alert(self, alert: SIEMAlert) -> None:
        """Store SIEM alert"""
        alert_data = {
            'siem_provider': alert.siem_provider.value,
            'alert_name': alert.alert_name,
            'severity': alert.severity.value,
            'created_time': alert.created_time.isoformat(),
            'description': alert.description,
            'affected_assets': json.dumps(alert.affected_assets),
            'indicators': json.dumps(alert.indicators),
            'raw_alert': json.dumps(alert.raw_alert)
        }
        
        await self.redis.hset(f"siem_alert:{alert.alert_id}", mapping=alert_data)
        await self.redis.expire(f"siem_alert:{alert.alert_id}", 86400 * 30)  # 30 days
        await self.redis.lpush("recent_siem_alerts", alert.alert_id)
    
    async def _respond_to_alert(self, alert: SIEMAlert) -> None:
        """Respond to SIEM alert"""
        try:
            if alert.severity in [EventSeverity.HIGH, EventSeverity.CRITICAL]:
                response_data = {
                    'alert_id': alert.alert_id,
                    'siem_provider': alert.siem_provider.value,
                    'alert_name': alert.alert_name,
                    'severity': alert.severity.value,
                    'response_time': datetime.utcnow().isoformat(),
                    'recommended_actions': [
                        'Investigate affected assets',
                        'Check for additional indicators',
                        'Review related security events',
                        'Consider incident response activation'
                    ]
                }
                
                await self.redis.lpush("security_incident_queue", json.dumps(response_data))
                self.logger.warning(f"High-priority SIEM alert received: {alert.alert_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to respond to alert: {str(e)}")
    
    async def get_siem_status(self) -> Dict[str, Any]:
        """Get SIEM integration status"""
        try:
            status = {
                'configured_siems': len(self.siem_configs),
                'active_connections': 0,
                'events_queued': self.event_queue.qsize(),
                'recent_alerts': 0,
                'providers': {}
            }
            
            for provider_name, siem_config in self.siem_configs.items():
                connection_ok = await self._test_siem_connection(siem_config)
                if connection_ok:
                    status['active_connections'] += 1
                
                status['providers'][provider_name] = {
                    'provider_type': siem_config.provider.value,
                    'connection_status': 'connected' if connection_ok else 'disconnected',
                    'endpoint': siem_config.endpoint,
                    'batch_size': siem_config.batch_size
                }
            
            alert_count = await self.redis.llen("recent_siem_alerts")
            status['recent_alerts'] = alert_count or 0
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get SIEM status: {str(e)}")
            return {'error': str(e)}