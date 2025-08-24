"""
ML-Based Threat Detection and Anomaly Detection System
Advanced machine learning algorithms for detecting security threats and anomalies.

Author: Lance James, Unit 221B
"""

import asyncio
import logging
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import secrets
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import DBSCAN
from sklearn.neural_network import MLPClassifier
import redis
import pickle
import hashlib


class ThreatLevel(Enum):
    """Threat severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnomalyType(Enum):
    """Types of detected anomalies"""
    ACCESS_PATTERN = "access_pattern"
    TIME_BASED = "time_based"
    LOCATION_BASED = "location_based"
    FREQUENCY_BASED = "frequency_based"
    BEHAVIORAL = "behavioral"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    BRUTE_FORCE = "brute_force"
    UNUSUAL_CREDENTIAL = "unusual_credential"


class ModelType(Enum):
    """ML model types for different detection tasks"""
    ISOLATION_FOREST = "isolation_forest"
    NEURAL_NETWORK = "neural_network"
    CLUSTERING = "clustering"
    STATISTICAL = "statistical"
    ENSEMBLE = "ensemble"


@dataclass
class SecurityEvent:
    """Security event for analysis"""
    event_id: str
    user_id: str
    credential_id: str
    action: str
    timestamp: datetime
    source_ip: str
    user_agent: str
    location: Dict[str, Any]
    success: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Anomaly:
    """Detected anomaly"""
    anomaly_id: str
    anomaly_type: AnomalyType
    threat_level: ThreatLevel
    confidence_score: float
    affected_entities: List[str]
    detection_time: datetime
    event_ids: List[str]
    description: str
    recommended_actions: List[str]
    ml_model_used: ModelType
    feature_importance: Dict[str, float]
    false_positive_probability: float


@dataclass
class MLModel:
    """ML model for threat detection"""
    model_id: str
    model_type: ModelType
    model_data: bytes
    scaler_data: Optional[bytes]
    feature_names: List[str]
    training_date: datetime
    model_version: str
    accuracy_metrics: Dict[str, float]
    last_retrain: datetime


class ThreatDetectionSystem:
    """ML-based threat detection and anomaly detection system"""
    
    def __init__(self, config: Dict[str, Any], redis_client: redis.Redis):
        self.config = config
        self.redis = redis_client
        self.logger = logging.getLogger(__name__)
        self.models: Dict[str, MLModel] = {}
        self.anomaly_history: Dict[str, List[Anomaly]] = {}
        self.event_buffer: List[SecurityEvent] = []
        self.feature_extractors: Dict[str, callable] = {}
        self.baseline_profiles: Dict[str, Dict[str, Any]] = {}
        
    async def initialize_threat_detection(self) -> bool:
        """Initialize the threat detection system"""
        try:
            await self._load_existing_models()
            await self._initialize_feature_extractors()
            await self._load_baseline_profiles()
            
            detection_config = self.config.get('vault', {}).get('threat_detection', {})
            
            if detection_config.get('auto_train_models', True):
                await self._train_initial_models()
            
            if detection_config.get('enable_real_time', True):
                asyncio.create_task(self._real_time_monitoring())
            
            self.logger.info("Threat detection system initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize threat detection: {str(e)}")
            return False
    
    async def _load_existing_models(self) -> None:
        """Load existing ML models from storage"""
        try:
            model_keys = await self.redis.keys("ml_model:*")
            
            for key in model_keys:
                model_id = key.decode().split(':', 1)[1] if isinstance(key, bytes) else key.split(':', 1)[1]
                model_data = await self.redis.hgetall(key)
                
                if model_data:
                    ml_model = MLModel(
                        model_id=model_id,
                        model_type=ModelType(model_data[b'model_type'].decode()),
                        model_data=model_data[b'model_data'],
                        scaler_data=model_data.get(b'scaler_data'),
                        feature_names=json.loads(model_data[b'feature_names'].decode()),
                        training_date=datetime.fromisoformat(model_data[b'training_date'].decode()),
                        model_version=model_data[b'model_version'].decode(),
                        accuracy_metrics=json.loads(model_data[b'accuracy_metrics'].decode()),
                        last_retrain=datetime.fromisoformat(model_data[b'last_retrain'].decode())
                    )
                    
                    self.models[model_id] = ml_model
            
            self.logger.info(f"Loaded {len(self.models)} ML models")
            
        except Exception as e:
            self.logger.error(f"Failed to load models: {str(e)}")
    
    async def _initialize_feature_extractors(self) -> None:
        """Initialize feature extraction functions"""
        self.feature_extractors = {
            'time_based': self._extract_time_features,
            'behavioral': self._extract_behavioral_features,
            'location': self._extract_location_features,
            'access_pattern': self._extract_access_pattern_features,
            'frequency': self._extract_frequency_features,
            'credential_usage': self._extract_credential_usage_features
        }
    
    async def _load_baseline_profiles(self) -> None:
        """Load baseline user behavior profiles"""
        try:
            profile_keys = await self.redis.keys("user_profile:*")
            
            for key in profile_keys:
                user_id = key.decode().split(':', 1)[1] if isinstance(key, bytes) else key.split(':', 1)[1]
                profile_data = await self.redis.hgetall(key)
                
                if profile_data:
                    self.baseline_profiles[user_id] = {
                        'typical_hours': json.loads(profile_data.get(b'typical_hours', b'[]').decode()),
                        'common_locations': json.loads(profile_data.get(b'common_locations', b'[]').decode()),
                        'access_patterns': json.loads(profile_data.get(b'access_patterns', b'{}').decode()),
                        'credential_usage': json.loads(profile_data.get(b'credential_usage', b'{}').decode()),
                        'baseline_frequency': float(profile_data.get(b'baseline_frequency', b'0').decode())
                    }
            
            self.logger.info(f"Loaded {len(self.baseline_profiles)} user profiles")
            
        except Exception as e:
            self.logger.error(f"Failed to load baseline profiles: {str(e)}")
    
    async def _train_initial_models(self) -> None:
        """Train initial ML models using historical data"""
        try:
            historical_events = await self._get_historical_events()
            
            if len(historical_events) < 1000:
                self.logger.warning("Insufficient historical data for training, using default models")
                await self._create_default_models()
                return
            
            feature_matrix, labels = await self._prepare_training_data(historical_events)
            
            await self._train_isolation_forest(feature_matrix)
            await self._train_neural_network(feature_matrix, labels)
            await self._train_clustering_model(feature_matrix)
            
            self.logger.info("Initial ML models trained successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to train initial models: {str(e)}")
    
    async def _get_historical_events(self) -> List[SecurityEvent]:
        """Get historical security events for training"""
        events = []
        
        try:
            event_keys = await self.redis.keys("security_event:*")
            
            for key in event_keys[-10000:]:  # Get last 10k events
                event_data = await self.redis.hgetall(key)
                if event_data:
                    event = SecurityEvent(
                        event_id=event_data[b'event_id'].decode(),
                        user_id=event_data[b'user_id'].decode(),
                        credential_id=event_data[b'credential_id'].decode(),
                        action=event_data[b'action'].decode(),
                        timestamp=datetime.fromisoformat(event_data[b'timestamp'].decode()),
                        source_ip=event_data[b'source_ip'].decode(),
                        user_agent=event_data[b'user_agent'].decode(),
                        location=json.loads(event_data[b'location'].decode()),
                        success=event_data[b'success'].decode().lower() == 'true',
                        metadata=json.loads(event_data.get(b'metadata', b'{}').decode())
                    )
                    events.append(event)
            
        except Exception as e:
            self.logger.error(f"Failed to get historical events: {str(e)}")
        
        return events
    
    async def _prepare_training_data(self, events: List[SecurityEvent]) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare feature matrix and labels for training"""
        features = []
        labels = []
        
        for event in events:
            feature_vector = await self._extract_all_features(event)
            features.append(feature_vector)
            
            is_anomaly = await self._is_known_anomaly(event)
            labels.append(1 if is_anomaly else 0)
        
        return np.array(features), np.array(labels)
    
    async def _extract_all_features(self, event: SecurityEvent) -> List[float]:
        """Extract all features from a security event"""
        features = []
        
        for extractor_name, extractor_func in self.feature_extractors.items():
            event_features = await extractor_func(event)
            features.extend(event_features)
        
        return features
    
    async def _extract_time_features(self, event: SecurityEvent) -> List[float]:
        """Extract time-based features"""
        hour = event.timestamp.hour
        day_of_week = event.timestamp.weekday()
        minute = event.timestamp.minute
        
        is_weekend = 1.0 if day_of_week >= 5 else 0.0
        is_business_hours = 1.0 if 8 <= hour <= 18 else 0.0
        is_night = 1.0 if hour >= 22 or hour <= 6 else 0.0
        
        return [hour / 24.0, day_of_week / 7.0, minute / 60.0, is_weekend, is_business_hours, is_night]
    
    async def _extract_behavioral_features(self, event: SecurityEvent) -> List[float]:
        """Extract behavioral features based on user baseline"""
        user_profile = self.baseline_profiles.get(event.user_id, {})
        
        typical_hours = user_profile.get('typical_hours', [])
        current_hour = event.timestamp.hour
        hour_deviation = min([abs(current_hour - h) for h in typical_hours]) if typical_hours else 12
        
        common_locations = user_profile.get('common_locations', [])
        location_match = 1.0 if any(
            loc.get('country') == event.location.get('country') for loc in common_locations
        ) else 0.0
        
        baseline_frequency = user_profile.get('baseline_frequency', 1.0)
        current_frequency = len([e for e in self.event_buffer[-100:] if e.user_id == event.user_id])
        frequency_ratio = current_frequency / max(baseline_frequency, 1.0)
        
        return [hour_deviation / 12.0, location_match, min(frequency_ratio, 10.0) / 10.0]
    
    async def _extract_location_features(self, event: SecurityEvent) -> List[float]:
        """Extract location-based features"""
        country = event.location.get('country', 'unknown')
        city = event.location.get('city', 'unknown')
        
        is_known_country = 1.0 if country in ['US', 'CA', 'GB', 'AU'] else 0.0
        has_location = 1.0 if country != 'unknown' else 0.0
        
        user_profile = self.baseline_profiles.get(event.user_id, {})
        common_locations = user_profile.get('common_locations', [])
        
        location_similarity = 0.0
        if common_locations:
            for loc in common_locations:
                if loc.get('country') == country:
                    location_similarity = 1.0
                    if loc.get('city') == city:
                        location_similarity = 2.0
                        break
        
        return [is_known_country, has_location, location_similarity / 2.0]
    
    async def _extract_access_pattern_features(self, event: SecurityEvent) -> List[float]:
        """Extract access pattern features"""
        action_type = event.action
        success = 1.0 if event.success else 0.0
        
        is_read = 1.0 if 'read' in action_type.lower() else 0.0
        is_write = 1.0 if any(w in action_type.lower() for w in ['write', 'create', 'update']) else 0.0
        is_delete = 1.0 if 'delete' in action_type.lower() else 0.0
        is_admin = 1.0 if 'admin' in action_type.lower() else 0.0
        
        credential_type_hash = hash(event.credential_id) % 100 / 100.0
        
        return [success, is_read, is_write, is_delete, is_admin, credential_type_hash]
    
    async def _extract_frequency_features(self, event: SecurityEvent) -> List[float]:
        """Extract frequency-based features"""
        now = datetime.utcnow()
        
        last_hour_events = len([
            e for e in self.event_buffer 
            if e.user_id == event.user_id and (now - e.timestamp).total_seconds() < 3600
        ])
        
        last_day_events = len([
            e for e in self.event_buffer 
            if e.user_id == event.user_id and (now - e.timestamp).total_seconds() < 86400
        ])
        
        same_ip_events = len([
            e for e in self.event_buffer 
            if e.source_ip == event.source_ip and (now - e.timestamp).total_seconds() < 3600
        ])
        
        return [min(last_hour_events, 50) / 50.0, min(last_day_events, 500) / 500.0, min(same_ip_events, 20) / 20.0]
    
    async def _extract_credential_usage_features(self, event: SecurityEvent) -> List[float]:
        """Extract credential usage features"""
        credential_age_days = 30  # Placeholder - would calculate from credential creation date
        credential_last_used_days = 1  # Placeholder - would calculate from last usage
        
        is_shared_credential = 0.0  # Would check if credential is used by multiple users
        is_privileged = 1.0 if 'admin' in event.credential_id.lower() else 0.0
        
        user_agent_entropy = len(set(event.user_agent.lower())) / max(len(event.user_agent), 1)
        
        return [
            min(credential_age_days, 365) / 365.0,
            min(credential_last_used_days, 30) / 30.0,
            is_shared_credential,
            is_privileged,
            user_agent_entropy
        ]
    
    async def _is_known_anomaly(self, event: SecurityEvent) -> bool:
        """Check if event is a known anomaly (for training)"""
        anomaly_indicators = await self.redis.sismember("known_anomalies", event.event_id)
        return bool(anomaly_indicators)
    
    async def _train_isolation_forest(self, feature_matrix: np.ndarray) -> None:
        """Train isolation forest for anomaly detection"""
        try:
            scaler = StandardScaler()
            scaled_features = scaler.fit_transform(feature_matrix)
            
            isolation_forest = IsolationForest(
                contamination=0.1,
                random_state=42,
                n_estimators=200
            )
            isolation_forest.fit(scaled_features)
            
            model_data = pickle.dumps(isolation_forest)
            scaler_data = pickle.dumps(scaler)
            
            ml_model = MLModel(
                model_id="isolation_forest_v1",
                model_type=ModelType.ISOLATION_FOREST,
                model_data=model_data,
                scaler_data=scaler_data,
                feature_names=list(self.feature_extractors.keys()),
                training_date=datetime.utcnow(),
                model_version="1.0",
                accuracy_metrics={"contamination": 0.1},
                last_retrain=datetime.utcnow()
            )
            
            self.models["isolation_forest_v1"] = ml_model
            await self._save_model(ml_model)
            
        except Exception as e:
            self.logger.error(f"Failed to train isolation forest: {str(e)}")
    
    async def _train_neural_network(self, feature_matrix: np.ndarray, labels: np.ndarray) -> None:
        """Train neural network for threat classification"""
        try:
            scaler = StandardScaler()
            scaled_features = scaler.fit_transform(feature_matrix)
            
            mlp = MLPClassifier(
                hidden_layer_sizes=(100, 50),
                activation='relu',
                solver='adam',
                max_iter=1000,
                random_state=42
            )
            mlp.fit(scaled_features, labels)
            
            model_data = pickle.dumps(mlp)
            scaler_data = pickle.dumps(scaler)
            
            score = mlp.score(scaled_features, labels)
            
            ml_model = MLModel(
                model_id="neural_network_v1",
                model_type=ModelType.NEURAL_NETWORK,
                model_data=model_data,
                scaler_data=scaler_data,
                feature_names=list(self.feature_extractors.keys()),
                training_date=datetime.utcnow(),
                model_version="1.0",
                accuracy_metrics={"accuracy": score},
                last_retrain=datetime.utcnow()
            )
            
            self.models["neural_network_v1"] = ml_model
            await self._save_model(ml_model)
            
        except Exception as e:
            self.logger.error(f"Failed to train neural network: {str(e)}")
    
    async def _train_clustering_model(self, feature_matrix: np.ndarray) -> None:
        """Train clustering model for behavioral analysis"""
        try:
            scaler = StandardScaler()
            scaled_features = scaler.fit_transform(feature_matrix)
            
            pca = PCA(n_components=10)
            reduced_features = pca.fit_transform(scaled_features)
            
            dbscan = DBSCAN(eps=0.5, min_samples=5)
            dbscan.fit(reduced_features)
            
            model_data = pickle.dumps(dbscan)
            scaler_data = pickle.dumps(scaler)
            pca_data = pickle.dumps(pca)
            
            ml_model = MLModel(
                model_id="clustering_v1",
                model_type=ModelType.CLUSTERING,
                model_data=model_data,
                scaler_data=scaler_data,
                feature_names=list(self.feature_extractors.keys()),
                training_date=datetime.utcnow(),
                model_version="1.0",
                accuracy_metrics={"n_clusters": len(set(dbscan.labels_))},
                last_retrain=datetime.utcnow()
            )
            
            ml_model.metadata = {'pca_data': pca_data}
            self.models["clustering_v1"] = ml_model
            await self._save_model(ml_model)
            
        except Exception as e:
            self.logger.error(f"Failed to train clustering model: {str(e)}")
    
    async def _save_model(self, model: MLModel) -> None:
        """Save ML model to Redis"""
        model_data = {
            'model_type': model.model_type.value,
            'model_data': model.model_data,
            'scaler_data': model.scaler_data or b'',
            'feature_names': json.dumps(model.feature_names),
            'training_date': model.training_date.isoformat(),
            'model_version': model.model_version,
            'accuracy_metrics': json.dumps(model.accuracy_metrics),
            'last_retrain': model.last_retrain.isoformat()
        }
        
        await self.redis.hset(f"ml_model:{model.model_id}", mapping=model_data)
        await self.redis.expire(f"ml_model:{model.model_id}", 86400 * 365)  # 1 year
    
    async def _create_default_models(self) -> None:
        """Create default models when insufficient training data"""
        default_features = [[0.5] * 20 for _ in range(100)]  # Dummy data
        
        await self._train_isolation_forest(np.array(default_features))
        self.logger.info("Created default isolation forest model")
    
    async def analyze_security_event(self, event: SecurityEvent) -> List[Anomaly]:
        """Analyze a security event for anomalies"""
        try:
            self.event_buffer.append(event)
            if len(self.event_buffer) > 10000:
                self.event_buffer = self.event_buffer[-5000:]
            
            await self._store_security_event(event)
            
            detected_anomalies = []
            
            for model_id, model in self.models.items():
                anomaly = await self._detect_anomaly_with_model(event, model)
                if anomaly:
                    detected_anomalies.append(anomaly)
            
            for anomaly in detected_anomalies:
                await self._store_anomaly(anomaly)
                await self._send_threat_alert(anomaly)
            
            return detected_anomalies
            
        except Exception as e:
            self.logger.error(f"Failed to analyze security event: {str(e)}")
            return []
    
    async def _store_security_event(self, event: SecurityEvent) -> None:
        """Store security event in Redis"""
        event_data = {
            'event_id': event.event_id,
            'user_id': event.user_id,
            'credential_id': event.credential_id,
            'action': event.action,
            'timestamp': event.timestamp.isoformat(),
            'source_ip': event.source_ip,
            'user_agent': event.user_agent,
            'location': json.dumps(event.location),
            'success': str(event.success),
            'metadata': json.dumps(event.metadata)
        }
        
        await self.redis.hset(f"security_event:{event.event_id}", mapping=event_data)
        await self.redis.expire(f"security_event:{event.event_id}", 86400 * 90)  # 90 days
    
    async def _detect_anomaly_with_model(self, event: SecurityEvent, model: MLModel) -> Optional[Anomaly]:
        """Detect anomaly using specific ML model"""
        try:
            features = await self._extract_all_features(event)
            feature_array = np.array([features])
            
            if model.scaler_data:
                scaler = pickle.loads(model.scaler_data)
                feature_array = scaler.transform(feature_array)
            
            ml_model = pickle.loads(model.model_data)
            
            if model.model_type == ModelType.ISOLATION_FOREST:
                prediction = ml_model.decision_function(feature_array)[0]
                is_anomaly = ml_model.predict(feature_array)[0] == -1
                confidence = abs(prediction)
                
                if is_anomaly and confidence > 0.1:
                    return Anomaly(
                        anomaly_id=secrets.token_hex(16),
                        anomaly_type=AnomalyType.BEHAVIORAL,
                        threat_level=self._calculate_threat_level(confidence),
                        confidence_score=confidence,
                        affected_entities=[event.user_id, event.credential_id],
                        detection_time=datetime.utcnow(),
                        event_ids=[event.event_id],
                        description=f"Isolation Forest detected behavioral anomaly (score: {confidence:.3f})",
                        recommended_actions=["Investigate user behavior", "Review access patterns"],
                        ml_model_used=model.model_type,
                        feature_importance={"behavioral": confidence},
                        false_positive_probability=0.1
                    )
            
            elif model.model_type == ModelType.NEURAL_NETWORK:
                prediction_proba = ml_model.predict_proba(feature_array)[0]
                anomaly_probability = prediction_proba[1] if len(prediction_proba) > 1 else 0
                
                if anomaly_probability > 0.7:
                    return Anomaly(
                        anomaly_id=secrets.token_hex(16),
                        anomaly_type=AnomalyType.ACCESS_PATTERN,
                        threat_level=self._calculate_threat_level(anomaly_probability),
                        confidence_score=anomaly_probability,
                        affected_entities=[event.user_id, event.credential_id],
                        detection_time=datetime.utcnow(),
                        event_ids=[event.event_id],
                        description=f"Neural network detected access pattern anomaly (confidence: {anomaly_probability:.3f})",
                        recommended_actions=["Review access logs", "Verify user identity"],
                        ml_model_used=model.model_type,
                        feature_importance={"access_pattern": anomaly_probability},
                        false_positive_probability=0.05
                    )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to detect anomaly with model {model.model_id}: {str(e)}")
            return None
    
    def _calculate_threat_level(self, confidence: float) -> ThreatLevel:
        """Calculate threat level based on confidence score"""
        if confidence >= 0.9:
            return ThreatLevel.CRITICAL
        elif confidence >= 0.7:
            return ThreatLevel.HIGH
        elif confidence >= 0.5:
            return ThreatLevel.MEDIUM
        else:
            return ThreatLevel.LOW
    
    async def _store_anomaly(self, anomaly: Anomaly) -> None:
        """Store detected anomaly"""
        anomaly_data = {
            'anomaly_type': anomaly.anomaly_type.value,
            'threat_level': anomaly.threat_level.value,
            'confidence_score': str(anomaly.confidence_score),
            'affected_entities': json.dumps(anomaly.affected_entities),
            'detection_time': anomaly.detection_time.isoformat(),
            'event_ids': json.dumps(anomaly.event_ids),
            'description': anomaly.description,
            'recommended_actions': json.dumps(anomaly.recommended_actions),
            'ml_model_used': anomaly.ml_model_used.value,
            'feature_importance': json.dumps(anomaly.feature_importance),
            'false_positive_probability': str(anomaly.false_positive_probability)
        }
        
        await self.redis.hset(f"anomaly:{anomaly.anomaly_id}", mapping=anomaly_data)
        await self.redis.expire(f"anomaly:{anomaly.anomaly_id}", 86400 * 180)  # 6 months
        
        await self.redis.zadd("anomalies_by_time", {anomaly.anomaly_id: anomaly.detection_time.timestamp()})
        await self.redis.sadd(f"user_anomalies:{anomaly.affected_entities[0]}", anomaly.anomaly_id)
    
    async def _send_threat_alert(self, anomaly: Anomaly) -> None:
        """Send threat alert notifications"""
        try:
            alert_data = {
                'anomaly_id': anomaly.anomaly_id,
                'threat_level': anomaly.threat_level.value,
                'description': anomaly.description,
                'affected_entities': anomaly.affected_entities,
                'detection_time': anomaly.detection_time.isoformat(),
                'recommended_actions': anomaly.recommended_actions
            }
            
            if anomaly.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                await self.redis.lpush("urgent_alerts", json.dumps(alert_data))
            else:
                await self.redis.lpush("security_alerts", json.dumps(alert_data))
            
            self.logger.warning(f"Threat detected: {anomaly.description}")
            
        except Exception as e:
            self.logger.error(f"Failed to send threat alert: {str(e)}")
    
    async def _real_time_monitoring(self) -> None:
        """Real-time monitoring loop"""
        while True:
            try:
                await self._update_baseline_profiles()
                await self._retrain_models_if_needed()
                await self._cleanup_old_data()
                await asyncio.sleep(300)  # 5 minutes
                
            except Exception as e:
                self.logger.error(f"Real-time monitoring error: {str(e)}")
                await asyncio.sleep(60)
    
    async def _update_baseline_profiles(self) -> None:
        """Update user baseline profiles"""
        try:
            for user_id in set(event.user_id for event in self.event_buffer[-1000:]):
                user_events = [e for e in self.event_buffer if e.user_id == user_id]
                
                if len(user_events) >= 10:
                    profile = await self._calculate_user_profile(user_events)
                    self.baseline_profiles[user_id] = profile
                    await self._save_user_profile(user_id, profile)
            
        except Exception as e:
            self.logger.error(f"Failed to update baseline profiles: {str(e)}")
    
    async def _calculate_user_profile(self, events: List[SecurityEvent]) -> Dict[str, Any]:
        """Calculate user behavioral profile"""
        hours = [e.timestamp.hour for e in events]
        locations = [e.location for e in events]
        
        typical_hours = list(set(hours))
        common_locations = locations[-5:]  # Last 5 unique locations
        
        return {
            'typical_hours': typical_hours,
            'common_locations': common_locations,
            'access_patterns': {'most_common_action': max(set(e.action for e in events), key=lambda x: sum(1 for e in events if e.action == x))},
            'credential_usage': {'unique_credentials': len(set(e.credential_id for e in events))},
            'baseline_frequency': len(events) / max(1, (events[-1].timestamp - events[0].timestamp).days or 1)
        }
    
    async def _save_user_profile(self, user_id: str, profile: Dict[str, Any]) -> None:
        """Save user profile to Redis"""
        profile_data = {
            'typical_hours': json.dumps(profile['typical_hours']),
            'common_locations': json.dumps(profile['common_locations']),
            'access_patterns': json.dumps(profile['access_patterns']),
            'credential_usage': json.dumps(profile['credential_usage']),
            'baseline_frequency': str(profile['baseline_frequency']),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        await self.redis.hset(f"user_profile:{user_id}", mapping=profile_data)
        await self.redis.expire(f"user_profile:{user_id}", 86400 * 365)  # 1 year
    
    async def _retrain_models_if_needed(self) -> None:
        """Retrain models if they're outdated"""
        try:
            for model_id, model in self.models.items():
                days_since_retrain = (datetime.utcnow() - model.last_retrain).days
                
                if days_since_retrain > 30:  # Retrain monthly
                    self.logger.info(f"Retraining model {model_id}")
                    await self._retrain_model(model)
            
        except Exception as e:
            self.logger.error(f"Failed to retrain models: {str(e)}")
    
    async def _retrain_model(self, model: MLModel) -> None:
        """Retrain a specific model"""
        try:
            recent_events = await self._get_historical_events()
            feature_matrix, labels = await self._prepare_training_data(recent_events[-5000:])
            
            if model.model_type == ModelType.ISOLATION_FOREST:
                await self._train_isolation_forest(feature_matrix)
            elif model.model_type == ModelType.NEURAL_NETWORK:
                await self._train_neural_network(feature_matrix, labels)
            
        except Exception as e:
            self.logger.error(f"Failed to retrain model {model.model_id}: {str(e)}")
    
    async def _cleanup_old_data(self) -> None:
        """Clean up old events and anomalies"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=90)
            
            await self.redis.zremrangebyscore("anomalies_by_time", 0, cutoff_time.timestamp())
            
            if len(self.event_buffer) > 5000:
                self.event_buffer = self.event_buffer[-2500:]
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {str(e)}")
    
    async def get_threat_summary(self) -> Dict[str, Any]:
        """Get threat detection summary"""
        try:
            total_anomalies = await self.redis.zcard("anomalies_by_time")
            
            recent_anomalies = await self.redis.zrevrangebyscore(
                "anomalies_by_time", 
                (datetime.utcnow() - timedelta(hours=24)).timestamp(),
                datetime.utcnow().timestamp()
            )
            
            threat_levels = {level.value: 0 for level in ThreatLevel}
            
            for anomaly_id in recent_anomalies[-100:]:  # Last 100 anomalies
                anomaly_data = await self.redis.hgetall(f"anomaly:{anomaly_id.decode()}")
                if anomaly_data:
                    threat_level = anomaly_data.get(b'threat_level', b'low').decode()
                    threat_levels[threat_level] += 1
            
            return {
                'total_anomalies': total_anomalies,
                'anomalies_last_24h': len(recent_anomalies),
                'threat_levels_distribution': threat_levels,
                'active_models': len(self.models),
                'baseline_profiles': len(self.baseline_profiles),
                'system_status': 'active'
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get threat summary: {str(e)}")
            return {'error': str(e)}