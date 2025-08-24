#!/usr/bin/env python3
"""
Intelligent Playbook Auto-Generation System for ClaudeOps hAIveMind

This module implements AI-powered playbook generation from successful incident resolutions:
- Analyzes incident resolution patterns from memory system
- Extracts common procedures and creates playbook templates
- Uses pattern recognition to identify recurring incident types
- Generates structured playbooks with human review workflow
- Integrates with hAIveMind for cross-agent learning and validation
"""

import asyncio
import json
import logging
import re
import time
import uuid
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

@dataclass
class IncidentPattern:
    """Represents a detected pattern in incident resolutions"""
    pattern_id: str
    incident_type: str
    common_systems: List[str]
    resolution_steps: List[str]
    frequency: int
    success_rate: float
    avg_resolution_time: float
    keywords: List[str]
    severity_distribution: Dict[str, int]
    created_at: datetime
    last_seen: datetime

@dataclass
class PlaybookSuggestion:
    """Represents an auto-generated playbook suggestion"""
    suggestion_id: str
    title: str
    description: str
    category: str
    pattern_id: str
    confidence_score: float
    playbook_spec: Dict[str, Any]
    supporting_incidents: List[str]
    human_review_status: str  # "pending", "approved", "rejected", "needs_revision"
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewer_notes: Optional[str] = None

@dataclass
class PatternAnalysisResult:
    """Results from pattern analysis of incidents"""
    patterns_found: List[IncidentPattern]
    new_patterns: List[IncidentPattern]
    updated_patterns: List[IncidentPattern]
    playbook_suggestions: List[PlaybookSuggestion]
    analysis_metadata: Dict[str, Any]

class PlaybookAutoGenerator:
    """AI-powered playbook generation from incident resolution patterns"""
    
    def __init__(self, memory_storage, config: Dict[str, Any]):
        self.memory_storage = memory_storage
        self.config = config
        self.patterns_cache = {}
        self.suggestions_cache = {}
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 3),
            min_df=2
        )
        
        # Pattern detection thresholds
        self.min_pattern_frequency = config.get('min_pattern_frequency', 3)
        self.min_success_rate = config.get('min_success_rate', 0.8)
        self.similarity_threshold = config.get('similarity_threshold', 0.7)
        self.confidence_threshold = config.get('confidence_threshold', 0.75)
        
        # Initialize pattern storage
        self._init_pattern_storage()
    
    def _init_pattern_storage(self):
        """Initialize pattern storage in memory system"""
        try:
            # Create collections for patterns and suggestions if they don't exist
            if hasattr(self.memory_storage, 'chroma_client'):
                try:
                    self.memory_storage.chroma_client.get_collection("incident_patterns")
                except:
                    self.memory_storage.chroma_client.create_collection(
                        name="incident_patterns",
                        metadata={"description": "Detected incident resolution patterns"}
                    )
                
                try:
                    self.memory_storage.chroma_client.get_collection("playbook_suggestions")
                except:
                    self.memory_storage.chroma_client.create_collection(
                        name="playbook_suggestions", 
                        metadata={"description": "Auto-generated playbook suggestions"}
                    )
        except Exception as e:
            logger.error(f"Failed to initialize pattern storage: {e}")
    
    async def analyze_incident_patterns(self, 
                                      lookback_days: int = 30,
                                      min_incidents: int = 5) -> PatternAnalysisResult:
        """
        Analyze incident memories to identify patterns and generate playbook suggestions
        
        Args:
            lookback_days: How many days back to analyze incidents
            min_incidents: Minimum number of incidents needed to detect patterns
            
        Returns:
            PatternAnalysisResult with detected patterns and suggestions
        """
        try:
            logger.info(f"🔍 Starting incident pattern analysis (lookback: {lookback_days} days)")
            
            # Retrieve incident memories from the last N days
            cutoff_date = datetime.now() - timedelta(days=lookback_days)
            incidents = await self._get_incident_memories(cutoff_date)
            
            if len(incidents) < min_incidents:
                logger.warning(f"Insufficient incidents for analysis: {len(incidents)} < {min_incidents}")
                return PatternAnalysisResult([], [], [], [], {
                    "total_incidents": len(incidents),
                    "analysis_date": datetime.now(),
                    "status": "insufficient_data"
                })
            
            logger.info(f"📊 Analyzing {len(incidents)} incidents for patterns")
            
            # Extract features and cluster incidents
            incident_features = self._extract_incident_features(incidents)
            clusters = self._cluster_incidents(incident_features)
            
            # Detect patterns from clusters
            patterns = await self._detect_patterns_from_clusters(incidents, clusters)
            
            # Compare with existing patterns
            existing_patterns = await self._load_existing_patterns()
            new_patterns, updated_patterns = self._compare_patterns(patterns, existing_patterns)
            
            # Generate playbook suggestions from patterns
            suggestions = await self._generate_playbook_suggestions(patterns)
            
            # Store new patterns and suggestions
            await self._store_patterns(new_patterns + updated_patterns)
            await self._store_suggestions(suggestions)
            
            # Broadcast findings to hAIveMind
            if new_patterns or suggestions:
                await self._broadcast_pattern_discovery(new_patterns, suggestions)
            
            result = PatternAnalysisResult(
                patterns_found=patterns,
                new_patterns=new_patterns,
                updated_patterns=updated_patterns,
                playbook_suggestions=suggestions,
                analysis_metadata={
                    "total_incidents": len(incidents),
                    "clusters_found": len(set(clusters)),
                    "patterns_detected": len(patterns),
                    "new_patterns": len(new_patterns),
                    "updated_patterns": len(updated_patterns),
                    "suggestions_generated": len(suggestions),
                    "analysis_date": datetime.now(),
                    "lookback_days": lookback_days,
                    "status": "completed"
                }
            )
            
            logger.info(f"✅ Pattern analysis completed: {len(patterns)} patterns, {len(suggestions)} suggestions")
            return result
            
        except Exception as e:
            logger.error(f"💥 Pattern analysis failed: {e}")
            raise
    
    async def _get_incident_memories(self, cutoff_date: datetime) -> List[Dict[str, Any]]:
        """Retrieve incident memories from the memory system"""
        try:
            # Search for incident memories
            search_results = await self.memory_storage.search_memories(
                query="incident resolution procedure steps",
                category="incidents",
                limit=1000
            )
            
            incidents = []
            for result in search_results.get('memories', []):
                # Parse timestamp and filter by cutoff date
                try:
                    created_at = datetime.fromisoformat(result.get('timestamp', '').replace('Z', '+00:00'))
                    if created_at >= cutoff_date:
                        incidents.append(result)
                except:
                    # Include incidents without valid timestamps
                    incidents.append(result)
            
            # Also search for resolved incidents specifically
            resolved_search = await self.memory_storage.search_memories(
                query="resolved fixed solution procedure",
                category="incidents", 
                limit=500
            )
            
            for result in resolved_search.get('memories', []):
                if result not in incidents:  # Avoid duplicates
                    try:
                        created_at = datetime.fromisoformat(result.get('timestamp', '').replace('Z', '+00:00'))
                        if created_at >= cutoff_date:
                            incidents.append(result)
                    except:
                        incidents.append(result)
            
            logger.info(f"📥 Retrieved {len(incidents)} incident memories")
            return incidents
            
        except Exception as e:
            logger.error(f"Failed to retrieve incident memories: {e}")
            return []
    
    def _extract_incident_features(self, incidents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract features from incidents for pattern detection"""
        try:
            features = {
                'texts': [],
                'systems': [],
                'severities': [],
                'resolution_indicators': [],
                'metadata': []
            }
            
            for incident in incidents:
                content = incident.get('content', '')
                metadata = incident.get('metadata', {})
                
                # Extract text features
                features['texts'].append(content)
                
                # Extract system information
                systems = self._extract_systems_from_text(content)
                features['systems'].append(systems)
                
                # Extract severity
                severity = self._extract_severity_from_text(content)
                features['severities'].append(severity)
                
                # Check for resolution indicators
                has_resolution = self._has_resolution_indicators(content)
                features['resolution_indicators'].append(has_resolution)
                
                # Store metadata
                features['metadata'].append({
                    'id': incident.get('id'),
                    'timestamp': incident.get('timestamp'),
                    'machine_id': incident.get('machine_id'),
                    'metadata': metadata
                })
            
            logger.info(f"🔧 Extracted features from {len(incidents)} incidents")
            return features
            
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            return {'texts': [], 'systems': [], 'severities': [], 'resolution_indicators': [], 'metadata': []}
    
    def _extract_systems_from_text(self, text: str) -> List[str]:
        """Extract system names from incident text"""
        systems = []
        
        # Common system patterns
        system_patterns = [
            r'\b(elasticsearch|elastic)\b',
            r'\b(nginx|apache|httpd)\b',
            r'\b(mysql|postgresql|postgres|mongodb|redis)\b',
            r'\b(docker|kubernetes|k8s)\b',
            r'\b(jenkins|gitlab|github)\b',
            r'\b(grafana|prometheus|alertmanager)\b',
            r'\b(kafka|rabbitmq|celery)\b',
            r'\b(systemd|service)\b',
            r'\b(proxy\d+|scraper|telegram)\b'
        ]
        
        text_lower = text.lower()
        for pattern in system_patterns:
            matches = re.findall(pattern, text_lower)
            systems.extend(matches)
        
        return list(set(systems))  # Remove duplicates
    
    def _extract_severity_from_text(self, text: str) -> str:
        """Extract severity level from incident text"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['critical', 'down', 'outage', 'failed']):
            return 'critical'
        elif any(word in text_lower for word in ['high', 'urgent', 'error']):
            return 'high'
        elif any(word in text_lower for word in ['medium', 'warning', 'degraded']):
            return 'medium'
        else:
            return 'low'
    
    def _has_resolution_indicators(self, text: str) -> bool:
        """Check if incident text contains resolution indicators"""
        resolution_keywords = [
            'resolved', 'fixed', 'solution', 'restart', 'reboot',
            'cleared', 'restored', 'recovered', 'procedure',
            'steps taken', 'corrected', 'repaired'
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in resolution_keywords)
    
    def _cluster_incidents(self, features: Dict[str, Any]) -> List[int]:
        """Cluster incidents based on their features"""
        try:
            texts = features['texts']
            if not texts:
                return []
            
            # Vectorize text content
            text_vectors = self.vectorizer.fit_transform(texts)
            
            # Apply DBSCAN clustering
            clustering = DBSCAN(
                eps=1 - self.similarity_threshold,  # Convert similarity to distance
                min_samples=self.min_pattern_frequency,
                metric='cosine'
            )
            
            clusters = clustering.fit_predict(text_vectors.toarray())
            
            logger.info(f"🎯 Found {len(set(clusters))} clusters from {len(texts)} incidents")
            return clusters.tolist()
            
        except Exception as e:
            logger.error(f"Clustering failed: {e}")
            return [0] * len(features['texts'])  # Default to single cluster
    
    async def _detect_patterns_from_clusters(self, 
                                           incidents: List[Dict[str, Any]], 
                                           clusters: List[int]) -> List[IncidentPattern]:
        """Detect patterns from clustered incidents"""
        try:
            patterns = []
            cluster_groups = defaultdict(list)
            
            # Group incidents by cluster
            for i, cluster_id in enumerate(clusters):
                if cluster_id != -1:  # Ignore noise points
                    cluster_groups[cluster_id].append((i, incidents[i]))
            
            # Analyze each cluster
            for cluster_id, cluster_incidents in cluster_groups.items():
                if len(cluster_incidents) >= self.min_pattern_frequency:
                    pattern = await self._analyze_cluster_pattern(cluster_id, cluster_incidents)
                    if pattern and pattern.success_rate >= self.min_success_rate:
                        patterns.append(pattern)
            
            logger.info(f"🔍 Detected {len(patterns)} valid patterns")
            return patterns
            
        except Exception as e:
            logger.error(f"Pattern detection failed: {e}")
            return []
    
    async def _analyze_cluster_pattern(self, 
                                     cluster_id: int, 
                                     cluster_incidents: List[Tuple[int, Dict[str, Any]]]) -> Optional[IncidentPattern]:
        """Analyze a cluster to extract a pattern"""
        try:
            incidents = [incident for _, incident in cluster_incidents]
            
            # Extract common characteristics
            all_systems = []
            all_severities = []
            resolution_steps = []
            keywords = []
            timestamps = []
            
            resolved_count = 0
            
            for incident in incidents:
                content = incident.get('content', '')
                
                # Extract systems
                systems = self._extract_systems_from_text(content)
                all_systems.extend(systems)
                
                # Extract severity
                severity = self._extract_severity_from_text(content)
                all_severities.append(severity)
                
                # Extract resolution steps
                steps = self._extract_resolution_steps(content)
                resolution_steps.extend(steps)
                
                # Extract keywords
                words = self._extract_keywords(content)
                keywords.extend(words)
                
                # Check if resolved
                if self._has_resolution_indicators(content):
                    resolved_count += 1
                
                # Extract timestamp
                try:
                    timestamp = datetime.fromisoformat(incident.get('timestamp', '').replace('Z', '+00:00'))
                    timestamps.append(timestamp)
                except:
                    timestamps.append(datetime.now())
            
            # Calculate pattern characteristics
            common_systems = [system for system, count in Counter(all_systems).most_common(5)]
            severity_dist = dict(Counter(all_severities))
            common_steps = [step for step, count in Counter(resolution_steps).most_common(10) if count >= 2]
            top_keywords = [word for word, count in Counter(keywords).most_common(20) if count >= 2]
            
            success_rate = resolved_count / len(incidents) if incidents else 0
            
            # Calculate average resolution time (placeholder - would need more detailed tracking)
            avg_resolution_time = 3600.0  # Default 1 hour
            
            # Generate incident type from common keywords
            incident_type = self._generate_incident_type(top_keywords, common_systems)
            
            pattern = IncidentPattern(
                pattern_id=f"pattern_{cluster_id}_{int(time.time())}",
                incident_type=incident_type,
                common_systems=common_systems,
                resolution_steps=common_steps,
                frequency=len(incidents),
                success_rate=success_rate,
                avg_resolution_time=avg_resolution_time,
                keywords=top_keywords,
                severity_distribution=severity_dist,
                created_at=datetime.now(),
                last_seen=max(timestamps) if timestamps else datetime.now()
            )
            
            return pattern
            
        except Exception as e:
            logger.error(f"Cluster analysis failed for cluster {cluster_id}: {e}")
            return None
    
    def _extract_resolution_steps(self, text: str) -> List[str]:
        """Extract resolution steps from incident text"""
        steps = []
        
        # Look for numbered steps
        step_patterns = [
            r'\d+\.\s*([^.\n]+)',  # "1. Step description"
            r'Step \d+:\s*([^.\n]+)',  # "Step 1: Description"
            r'-\s*([^.\n]+)',  # "- Step description"
        ]
        
        for pattern in step_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            steps.extend([match.strip() for match in matches])
        
        # Look for action verbs indicating steps
        action_patterns = [
            r'(restart\w*\s+[^.\n]+)',
            r'(check\w*\s+[^.\n]+)',
            r'(verify\w*\s+[^.\n]+)',
            r'(run\w*\s+[^.\n]+)',
            r'(execute\w*\s+[^.\n]+)',
            r'(stop\w*\s+[^.\n]+)',
            r'(start\w*\s+[^.\n]+)',
        ]
        
        for pattern in action_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            steps.extend([match.strip() for match in matches])
        
        return list(set(steps))  # Remove duplicates
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from incident text"""
        # Remove common stop words and extract meaningful terms
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'was', 'are', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'}
        
        # Extract words, focusing on technical terms
        words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9_-]*\b', text.lower())
        keywords = [word for word in words if len(word) > 3 and word not in stop_words]
        
        return keywords
    
    def _generate_incident_type(self, keywords: List[str], systems: List[str]) -> str:
        """Generate a descriptive incident type from keywords and systems"""
        # Combine top keywords and systems
        all_terms = (keywords[:5] + systems[:3])
        
        if not all_terms:
            return "General Incident"
        
        # Create a readable incident type
        primary_term = all_terms[0].title()
        if len(all_terms) > 1:
            return f"{primary_term} {all_terms[1].title()} Issue"
        else:
            return f"{primary_term} Issue"
    
    async def _load_existing_patterns(self) -> List[IncidentPattern]:
        """Load existing patterns from storage"""
        try:
            # Search for existing patterns in memory
            search_results = await self.memory_storage.search_memories(
                query="incident pattern",
                category="patterns",
                limit=1000
            )
            
            patterns = []
            for result in search_results.get('memories', []):
                try:
                    pattern_data = json.loads(result.get('content', '{}'))
                    pattern = IncidentPattern(**pattern_data)
                    patterns.append(pattern)
                except Exception as e:
                    logger.warning(f"Failed to parse pattern: {e}")
            
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to load existing patterns: {e}")
            return []
    
    def _compare_patterns(self, 
                         new_patterns: List[IncidentPattern], 
                         existing_patterns: List[IncidentPattern]) -> Tuple[List[IncidentPattern], List[IncidentPattern]]:
        """Compare new patterns with existing ones to identify truly new patterns"""
        truly_new = []
        updated = []
        
        for new_pattern in new_patterns:
            similar_existing = None
            max_similarity = 0
            
            for existing_pattern in existing_patterns:
                similarity = self._calculate_pattern_similarity(new_pattern, existing_pattern)
                if similarity > max_similarity:
                    max_similarity = similarity
                    similar_existing = existing_pattern
            
            if max_similarity > self.similarity_threshold and similar_existing:
                # Update existing pattern
                updated_pattern = self._merge_patterns(similar_existing, new_pattern)
                updated.append(updated_pattern)
            else:
                # Truly new pattern
                truly_new.append(new_pattern)
        
        return truly_new, updated
    
    def _calculate_pattern_similarity(self, pattern1: IncidentPattern, pattern2: IncidentPattern) -> float:
        """Calculate similarity between two patterns"""
        try:
            # Compare keywords
            keywords1 = set(pattern1.keywords)
            keywords2 = set(pattern2.keywords)
            keyword_similarity = len(keywords1 & keywords2) / len(keywords1 | keywords2) if keywords1 | keywords2 else 0
            
            # Compare systems
            systems1 = set(pattern1.common_systems)
            systems2 = set(pattern2.common_systems)
            system_similarity = len(systems1 & systems2) / len(systems1 | systems2) if systems1 | systems2 else 0
            
            # Compare incident types
            type_similarity = 1.0 if pattern1.incident_type == pattern2.incident_type else 0.0
            
            # Weighted average
            return (keyword_similarity * 0.4 + system_similarity * 0.4 + type_similarity * 0.2)
            
        except Exception as e:
            logger.error(f"Pattern similarity calculation failed: {e}")
            return 0.0
    
    def _merge_patterns(self, existing: IncidentPattern, new: IncidentPattern) -> IncidentPattern:
        """Merge a new pattern with an existing similar one"""
        # Update frequency and other metrics
        total_frequency = existing.frequency + new.frequency
        
        # Weighted average for success rate
        combined_success_rate = (
            (existing.success_rate * existing.frequency + new.success_rate * new.frequency) / 
            total_frequency
        )
        
        # Merge keywords and systems
        combined_keywords = list(set(existing.keywords + new.keywords))
        combined_systems = list(set(existing.common_systems + new.common_systems))
        combined_steps = list(set(existing.resolution_steps + new.resolution_steps))
        
        # Merge severity distributions
        combined_severity = existing.severity_distribution.copy()
        for severity, count in new.severity_distribution.items():
            combined_severity[severity] = combined_severity.get(severity, 0) + count
        
        return IncidentPattern(
            pattern_id=existing.pattern_id,  # Keep existing ID
            incident_type=existing.incident_type,  # Keep existing type
            common_systems=combined_systems,
            resolution_steps=combined_steps,
            frequency=total_frequency,
            success_rate=combined_success_rate,
            avg_resolution_time=(existing.avg_resolution_time + new.avg_resolution_time) / 2,
            keywords=combined_keywords,
            severity_distribution=combined_severity,
            created_at=existing.created_at,  # Keep original creation time
            last_seen=max(existing.last_seen, new.last_seen)
        )
    
    async def _generate_playbook_suggestions(self, patterns: List[IncidentPattern]) -> List[PlaybookSuggestion]:
        """Generate playbook suggestions from detected patterns"""
        suggestions = []
        
        for pattern in patterns:
            if (pattern.frequency >= self.min_pattern_frequency and 
                pattern.success_rate >= self.min_success_rate):
                
                suggestion = await self._create_playbook_suggestion(pattern)
                if suggestion:
                    suggestions.append(suggestion)
        
        return suggestions
    
    async def _create_playbook_suggestion(self, pattern: IncidentPattern) -> Optional[PlaybookSuggestion]:
        """Create a playbook suggestion from a pattern"""
        try:
            # Generate playbook specification
            playbook_spec = self._generate_playbook_spec(pattern)
            
            # Calculate confidence score
            confidence = self._calculate_confidence_score(pattern)
            
            if confidence < self.confidence_threshold:
                return None
            
            # Create suggestion
            suggestion = PlaybookSuggestion(
                suggestion_id=f"suggestion_{pattern.pattern_id}_{int(time.time())}",
                title=f"Auto-Generated: {pattern.incident_type} Resolution",
                description=f"Automated playbook for resolving {pattern.incident_type} based on {pattern.frequency} similar incidents",
                category="auto-generated",
                pattern_id=pattern.pattern_id,
                confidence_score=confidence,
                playbook_spec=playbook_spec,
                supporting_incidents=[],  # Would need to track specific incident IDs
                human_review_status="pending",
                created_at=datetime.now()
            )
            
            return suggestion
            
        except Exception as e:
            logger.error(f"Failed to create playbook suggestion: {e}")
            return None
    
    def _generate_playbook_spec(self, pattern: IncidentPattern) -> Dict[str, Any]:
        """Generate a playbook specification from a pattern"""
        # Create parameters based on common systems
        parameters = []
        if pattern.common_systems:
            parameters.append({
                "name": "affected_system",
                "required": True,
                "description": f"System affected by the incident (common: {', '.join(pattern.common_systems[:3])})"
            })
        
        # Generate steps from resolution steps
        steps = []
        step_id = 1
        
        # Add initial assessment step
        steps.append({
            "id": f"assess_{step_id}",
            "name": "Assess Current Status",
            "action": "noop",
            "args": {
                "message": f"Assessing {pattern.incident_type} on ${{affected_system}}"
            }
        })
        step_id += 1
        
        # Add resolution steps based on pattern
        for resolution_step in pattern.resolution_steps[:5]:  # Limit to top 5 steps
            # Convert resolution step to playbook step
            if 'restart' in resolution_step.lower():
                steps.append({
                    "id": f"restart_{step_id}",
                    "name": f"Restart Service",
                    "action": "shell",
                    "args": {
                        "command": "sudo systemctl restart ${affected_system}"
                    }
                })
            elif 'check' in resolution_step.lower() or 'verify' in resolution_step.lower():
                steps.append({
                    "id": f"verify_{step_id}",
                    "name": "Verify Status",
                    "action": "shell", 
                    "args": {
                        "command": "systemctl is-active ${affected_system}"
                    }
                })
            else:
                # Generic step
                steps.append({
                    "id": f"step_{step_id}",
                    "name": resolution_step[:50],  # Truncate long descriptions
                    "action": "noop",
                    "args": {
                        "message": resolution_step
                    }
                })
            step_id += 1
        
        # Add final verification
        steps.append({
            "id": f"final_verify_{step_id}",
            "name": "Final Verification",
            "action": "noop",
            "args": {
                "message": "Verify that the issue has been resolved"
            }
        })
        
        return {
            "version": 1,
            "name": f"{pattern.incident_type} Resolution",
            "category": "auto-generated",
            "description": f"Auto-generated playbook for resolving {pattern.incident_type}",
            "parameters": parameters,
            "steps": steps,
            "metadata": {
                "auto_generated": True,
                "pattern_id": pattern.pattern_id,
                "confidence_score": self._calculate_confidence_score(pattern),
                "based_on_incidents": pattern.frequency,
                "success_rate": pattern.success_rate,
                "generated_at": datetime.now().isoformat()
            }
        }
    
    def _calculate_confidence_score(self, pattern: IncidentPattern) -> float:
        """Calculate confidence score for a pattern-based playbook"""
        # Factors that increase confidence:
        # - Higher frequency (more examples)
        # - Higher success rate
        # - More detailed resolution steps
        # - More recent incidents
        
        frequency_score = min(pattern.frequency / 10.0, 1.0)  # Normalize to 0-1
        success_score = pattern.success_rate
        detail_score = min(len(pattern.resolution_steps) / 5.0, 1.0)  # More steps = more detail
        
        # Time decay - more recent patterns get higher scores
        days_since_last = (datetime.now() - pattern.last_seen).days
        recency_score = max(0.1, 1.0 - (days_since_last / 30.0))  # Decay over 30 days
        
        # Weighted average
        confidence = (
            frequency_score * 0.3 +
            success_score * 0.4 +
            detail_score * 0.2 +
            recency_score * 0.1
        )
        
        return min(confidence, 1.0)
    
    async def _store_patterns(self, patterns: List[IncidentPattern]):
        """Store patterns in the memory system"""
        try:
            for pattern in patterns:
                await self.memory_storage.store_memory(
                    content=json.dumps(asdict(pattern), default=str),
                    category="patterns",
                    metadata={
                        "pattern_id": pattern.pattern_id,
                        "incident_type": pattern.incident_type,
                        "frequency": pattern.frequency,
                        "success_rate": pattern.success_rate,
                        "auto_generated": True
                    }
                )
            
            logger.info(f"💾 Stored {len(patterns)} patterns")
            
        except Exception as e:
            logger.error(f"Failed to store patterns: {e}")
    
    async def _store_suggestions(self, suggestions: List[PlaybookSuggestion]):
        """Store playbook suggestions in the memory system"""
        try:
            for suggestion in suggestions:
                await self.memory_storage.store_memory(
                    content=json.dumps(asdict(suggestion), default=str),
                    category="playbook_suggestions",
                    metadata={
                        "suggestion_id": suggestion.suggestion_id,
                        "title": suggestion.title,
                        "confidence_score": suggestion.confidence_score,
                        "human_review_status": suggestion.human_review_status,
                        "auto_generated": True
                    }
                )
            
            logger.info(f"💾 Stored {len(suggestions)} playbook suggestions")
            
        except Exception as e:
            logger.error(f"Failed to store suggestions: {e}")
    
    async def _broadcast_pattern_discovery(self, 
                                         new_patterns: List[IncidentPattern], 
                                         suggestions: List[PlaybookSuggestion]):
        """Broadcast pattern discoveries to hAIveMind agents"""
        try:
            if hasattr(self.memory_storage, 'broadcast_discovery'):
                message = f"🤖 Auto-generated {len(new_patterns)} new incident patterns and {len(suggestions)} playbook suggestions"
                
                pattern_summary = []
                for pattern in new_patterns[:3]:  # Limit to top 3
                    pattern_summary.append(f"- {pattern.incident_type} ({pattern.frequency} incidents, {pattern.success_rate:.1%} success)")
                
                if pattern_summary:
                    message += "\n\nNew Patterns:\n" + "\n".join(pattern_summary)
                
                await self.memory_storage.broadcast_discovery(
                    message=message,
                    category="playbook_generation",
                    severity="info"
                )
                
                logger.info("📡 Broadcasted pattern discovery to hAIveMind")
            
        except Exception as e:
            logger.error(f"Failed to broadcast pattern discovery: {e}")
    
    async def get_pending_suggestions(self, limit: int = 50) -> List[PlaybookSuggestion]:
        """Get pending playbook suggestions for human review"""
        try:
            search_results = await self.memory_storage.search_memories(
                query="human_review_status:pending",
                category="playbook_suggestions",
                limit=limit
            )
            
            suggestions = []
            for result in search_results.get('memories', []):
                try:
                    suggestion_data = json.loads(result.get('content', '{}'))
                    suggestion = PlaybookSuggestion(**suggestion_data)
                    if suggestion.human_review_status == "pending":
                        suggestions.append(suggestion)
                except Exception as e:
                    logger.warning(f"Failed to parse suggestion: {e}")
            
            return sorted(suggestions, key=lambda s: s.confidence_score, reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to get pending suggestions: {e}")
            return []
    
    async def review_suggestion(self, 
                              suggestion_id: str, 
                              status: str, 
                              reviewer_notes: Optional[str] = None) -> bool:
        """Review a playbook suggestion"""
        try:
            if status not in ["approved", "rejected", "needs_revision"]:
                raise ValueError("Invalid review status")
            
            # Find and update the suggestion
            search_results = await self.memory_storage.search_memories(
                query=f"suggestion_id:{suggestion_id}",
                category="playbook_suggestions",
                limit=1
            )
            
            if not search_results.get('memories'):
                return False
            
            memory = search_results['memories'][0]
            suggestion_data = json.loads(memory.get('content', '{}'))
            
            # Update review status
            suggestion_data['human_review_status'] = status
            suggestion_data['reviewed_at'] = datetime.now().isoformat()
            if reviewer_notes:
                suggestion_data['reviewer_notes'] = reviewer_notes
            
            # Store updated suggestion
            await self.memory_storage.store_memory(
                content=json.dumps(suggestion_data, default=str),
                category="playbook_suggestions",
                metadata={
                    **memory.get('metadata', {}),
                    "human_review_status": status,
                    "reviewed_at": datetime.now().isoformat()
                }
            )
            
            # If approved, create the actual playbook
            if status == "approved":
                await self._create_approved_playbook(suggestion_data)
            
            logger.info(f"✅ Reviewed suggestion {suggestion_id}: {status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to review suggestion: {e}")
            return False
    
    async def _create_approved_playbook(self, suggestion_data: Dict[str, Any]):
        """Create an approved playbook from a suggestion"""
        try:
            playbook_spec = suggestion_data.get('playbook_spec', {})
            
            # Store as a runbook in the memory system
            if hasattr(self.memory_storage, 'generate_runbook'):
                await self.memory_storage.generate_runbook(
                    title=suggestion_data.get('title', 'Auto-Generated Playbook'),
                    procedure=json.dumps(playbook_spec, indent=2),
                    system=', '.join(playbook_spec.get('parameters', [{}])[0].get('description', '').split('(common: ')[1].split(')')[0].split(', ') if '(common: ' in playbook_spec.get('parameters', [{}])[0].get('description', '') else ['general']),
                    prerequisites=[f"Pattern confidence: {suggestion_data.get('confidence_score', 0):.1%}"],
                    expected_outcome=f"Resolution of {suggestion_data.get('title', 'incident')}"
                )
            
            logger.info(f"📖 Created approved playbook: {suggestion_data.get('title')}")
            
        except Exception as e:
            logger.error(f"Failed to create approved playbook: {e}")
    
    async def get_pattern_statistics(self) -> Dict[str, Any]:
        """Get statistics about detected patterns and suggestions"""
        try:
            # Get pattern counts
            pattern_search = await self.memory_storage.search_memories(
                query="pattern_id",
                category="patterns",
                limit=1000
            )
            
            suggestion_search = await self.memory_storage.search_memories(
                query="suggestion_id", 
                category="playbook_suggestions",
                limit=1000
            )
            
            patterns = pattern_search.get('memories', [])
            suggestions = suggestion_search.get('memories', [])
            
            # Analyze suggestion statuses
            status_counts = defaultdict(int)
            confidence_scores = []
            
            for suggestion_mem in suggestions:
                try:
                    suggestion_data = json.loads(suggestion_mem.get('content', '{}'))
                    status = suggestion_data.get('human_review_status', 'unknown')
                    status_counts[status] += 1
                    
                    confidence = suggestion_data.get('confidence_score', 0)
                    confidence_scores.append(confidence)
                except:
                    pass
            
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            
            return {
                "total_patterns": len(patterns),
                "total_suggestions": len(suggestions),
                "suggestion_statuses": dict(status_counts),
                "average_confidence": avg_confidence,
                "high_confidence_suggestions": len([s for s in confidence_scores if s > 0.8]),
                "last_analysis": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get pattern statistics: {e}")
            return {}

    async def continuous_pattern_monitoring(self, interval_hours: int = 24):
        """Run continuous pattern monitoring and suggestion generation"""
        logger.info(f"🔄 Starting continuous pattern monitoring (every {interval_hours} hours)")
        
        while True:
            try:
                # Run pattern analysis
                result = await self.analyze_incident_patterns(
                    lookback_days=7,  # Analyze last week
                    min_incidents=3   # Lower threshold for continuous monitoring
                )
                
                if result.new_patterns or result.playbook_suggestions:
                    logger.info(f"🎯 Continuous monitoring found: {len(result.new_patterns)} new patterns, {len(result.playbook_suggestions)} suggestions")
                
                # Sleep until next analysis
                await asyncio.sleep(interval_hours * 3600)
                
            except Exception as e:
                logger.error(f"💥 Continuous monitoring error: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour before retry