#!/usr/bin/env python3
"""
Playbook Recommendation Engine for ClaudeOps hAIveMind

This module provides intelligent playbook recommendations based on:
- Current incident context and symptoms
- Historical pattern matching
- System state and configuration
- Agent expertise and availability
- Real-time monitoring data
"""

import asyncio
import json
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

@dataclass
class PlaybookRecommendation:
    """Represents a recommended playbook for a given context"""
    playbook_id: str
    title: str
    description: str
    relevance_score: float
    confidence_score: float
    reasoning: List[str]
    estimated_duration: int  # minutes
    required_permissions: List[str]
    affected_systems: List[str]
    prerequisites: List[str]
    success_probability: float
    similar_incidents: List[str]
    recommended_by: str  # agent or system that made recommendation
    created_at: datetime

@dataclass
class IncidentContext:
    """Context information for an ongoing incident"""
    incident_id: str
    title: str
    description: str
    affected_systems: List[str]
    severity: str
    symptoms: List[str]
    error_messages: List[str]
    monitoring_alerts: List[Dict[str, Any]]
    duration_minutes: int
    reporter: str
    current_status: str

class PlaybookRecommendationEngine:
    """Intelligent playbook recommendation system"""
    
    def __init__(self, memory_storage, playbook_generator, config: Dict[str, Any]):
        self.memory_storage = memory_storage
        self.playbook_generator = playbook_generator
        self.config = config
        
        # Recommendation thresholds
        self.min_relevance_score = config.get('min_relevance_score', 0.6)
        self.max_recommendations = config.get('max_recommendations', 5)
        self.context_window_hours = config.get('context_window_hours', 24)
        
        # Initialize vectorizer for text similarity
        self.vectorizer = TfidfVectorizer(
            max_features=500,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=1
        )
        
        # Cache for frequent lookups
        self.playbook_cache = {}
        self.pattern_cache = {}
        
    async def recommend_playbooks(self, 
                                incident_context: IncidentContext,
                                include_auto_generated: bool = True,
                                agent_context: Optional[Dict[str, Any]] = None) -> List[PlaybookRecommendation]:
        """
        Recommend playbooks for a given incident context
        
        Args:
            incident_context: Current incident information
            include_auto_generated: Whether to include auto-generated playbooks
            agent_context: Information about the requesting agent
            
        Returns:
            List of recommended playbooks sorted by relevance
        """
        try:
            logger.info(f"🎯 Generating playbook recommendations for: {incident_context.title}")
            
            # Get available playbooks
            available_playbooks = await self._get_available_playbooks(include_auto_generated)
            
            if not available_playbooks:
                logger.warning("No playbooks available for recommendations")
                return []
            
            # Score each playbook against the incident context
            recommendations = []
            
            for playbook in available_playbooks:
                recommendation = await self._score_playbook_relevance(
                    playbook, incident_context, agent_context
                )
                
                if recommendation and recommendation.relevance_score >= self.min_relevance_score:
                    recommendations.append(recommendation)
            
            # Sort by relevance score and limit results
            recommendations.sort(key=lambda r: r.relevance_score, reverse=True)
            recommendations = recommendations[:self.max_recommendations]
            
            # Enhance recommendations with additional context
            enhanced_recommendations = await self._enhance_recommendations(
                recommendations, incident_context
            )
            
            logger.info(f"✅ Generated {len(enhanced_recommendations)} playbook recommendations")
            return enhanced_recommendations
            
        except Exception as e:
            logger.error(f"💥 Playbook recommendation failed: {e}")
            return []
    
    async def _get_available_playbooks(self, include_auto_generated: bool) -> List[Dict[str, Any]]:
        """Get all available playbooks from the memory system"""
        try:
            playbooks = []
            
            # Get manual playbooks from runbooks category
            runbook_search = await self.memory_storage.search_memories(
                query="runbook playbook procedure",
                category="runbooks",
                limit=500
            )
            
            for memory in runbook_search.get('memories', []):
                playbook_data = {
                    'id': memory.get('id'),
                    'title': memory.get('metadata', {}).get('title', 'Unknown Playbook'),
                    'content': memory.get('content', ''),
                    'metadata': memory.get('metadata', {}),
                    'type': 'manual',
                    'created_at': memory.get('timestamp')
                }
                playbooks.append(playbook_data)
            
            # Get auto-generated playbooks if requested
            if include_auto_generated:
                suggestion_search = await self.memory_storage.search_memories(
                    query="human_review_status:approved",
                    category="playbook_suggestions",
                    limit=200
                )
                
                for memory in suggestion_search.get('memories', []):
                    try:
                        suggestion_data = json.loads(memory.get('content', '{}'))
                        if suggestion_data.get('human_review_status') == 'approved':
                            playbook_data = {
                                'id': suggestion_data.get('suggestion_id'),
                                'title': suggestion_data.get('title'),
                                'content': json.dumps(suggestion_data.get('playbook_spec', {})),
                                'metadata': {
                                    'confidence_score': suggestion_data.get('confidence_score'),
                                    'pattern_id': suggestion_data.get('pattern_id'),
                                    'auto_generated': True
                                },
                                'type': 'auto_generated',
                                'created_at': suggestion_data.get('created_at')
                            }
                            playbooks.append(playbook_data)
                    except Exception as e:
                        logger.warning(f"Failed to parse auto-generated playbook: {e}")
            
            logger.info(f"📚 Found {len(playbooks)} available playbooks")
            return playbooks
            
        except Exception as e:
            logger.error(f"Failed to get available playbooks: {e}")
            return []
    
    async def _score_playbook_relevance(self, 
                                      playbook: Dict[str, Any],
                                      incident_context: IncidentContext,
                                      agent_context: Optional[Dict[str, Any]]) -> Optional[PlaybookRecommendation]:
        """Score a playbook's relevance to an incident context"""
        try:
            # Extract playbook information
            playbook_content = playbook.get('content', '')
            playbook_metadata = playbook.get('metadata', {})
            
            # Calculate different relevance factors
            text_similarity = self._calculate_text_similarity(
                playbook_content, incident_context.description
            )
            
            system_match = self._calculate_system_match(
                playbook_content, incident_context.affected_systems
            )
            
            severity_match = self._calculate_severity_match(
                playbook_content, incident_context.severity
            )
            
            symptom_match = self._calculate_symptom_match(
                playbook_content, incident_context.symptoms
            )
            
            historical_success = await self._get_historical_success_rate(
                playbook['id'], incident_context.affected_systems
            )
            
            # Calculate weighted relevance score
            relevance_score = (
                text_similarity * 0.25 +
                system_match * 0.30 +
                severity_match * 0.15 +
                symptom_match * 0.20 +
                historical_success * 0.10
            )
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(
                playbook, relevance_score, agent_context
            )
            
            # Generate reasoning
            reasoning = self._generate_reasoning(
                text_similarity, system_match, severity_match, 
                symptom_match, historical_success
            )
            
            # Estimate duration and requirements
            estimated_duration = self._estimate_duration(playbook_content)
            required_permissions = self._extract_required_permissions(playbook_content)
            prerequisites = self._extract_prerequisites(playbook_content)
            
            # Find similar incidents
            similar_incidents = await self._find_similar_incidents(incident_context)
            
            recommendation = PlaybookRecommendation(
                playbook_id=playbook['id'],
                title=playbook.get('title', 'Unknown Playbook'),
                description=self._extract_description(playbook_content),
                relevance_score=relevance_score,
                confidence_score=confidence_score,
                reasoning=reasoning,
                estimated_duration=estimated_duration,
                required_permissions=required_permissions,
                affected_systems=incident_context.affected_systems,
                prerequisites=prerequisites,
                success_probability=historical_success,
                similar_incidents=similar_incidents,
                recommended_by=f"recommendation_engine_{self.memory_storage.agent_id}",
                created_at=datetime.now()
            )
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Failed to score playbook relevance: {e}")
            return None
    
    def _calculate_text_similarity(self, playbook_content: str, incident_description: str) -> float:
        """Calculate text similarity between playbook and incident description"""
        try:
            if not playbook_content or not incident_description:
                return 0.0
            
            # Vectorize both texts
            texts = [playbook_content.lower(), incident_description.lower()]
            vectors = self.vectorizer.fit_transform(texts)
            
            # Calculate cosine similarity
            similarity_matrix = cosine_similarity(vectors)
            return float(similarity_matrix[0, 1])
            
        except Exception as e:
            logger.warning(f"Text similarity calculation failed: {e}")
            return 0.0
    
    def _calculate_system_match(self, playbook_content: str, affected_systems: List[str]) -> float:
        """Calculate how well playbook systems match affected systems"""
        if not affected_systems:
            return 0.5  # Neutral score if no systems specified
        
        playbook_content_lower = playbook_content.lower()
        matches = 0
        
        for system in affected_systems:
            if system.lower() in playbook_content_lower:
                matches += 1
        
        return matches / len(affected_systems)
    
    def _calculate_severity_match(self, playbook_content: str, severity: str) -> float:
        """Calculate severity match between playbook and incident"""
        severity_keywords = {
            'critical': ['critical', 'emergency', 'urgent', 'down', 'outage'],
            'high': ['high', 'important', 'error', 'failure'],
            'medium': ['medium', 'warning', 'degraded', 'slow'],
            'low': ['low', 'minor', 'info', 'maintenance']
        }
        
        playbook_content_lower = playbook_content.lower()
        severity_lower = severity.lower()
        
        # Check if playbook mentions the same severity level
        if severity_lower in playbook_content_lower:
            return 1.0
        
        # Check for severity keywords
        for sev_level, keywords in severity_keywords.items():
            if sev_level == severity_lower:
                for keyword in keywords:
                    if keyword in playbook_content_lower:
                        return 0.8
        
        return 0.3  # Default neutral score
    
    def _calculate_symptom_match(self, playbook_content: str, symptoms: List[str]) -> float:
        """Calculate how well playbook addresses reported symptoms"""
        if not symptoms:
            return 0.5
        
        playbook_content_lower = playbook_content.lower()
        matches = 0
        
        for symptom in symptoms:
            symptom_words = symptom.lower().split()
            for word in symptom_words:
                if len(word) > 3 and word in playbook_content_lower:
                    matches += 1
                    break
        
        return matches / len(symptoms)
    
    async def _get_historical_success_rate(self, playbook_id: str, systems: List[str]) -> float:
        """Get historical success rate for this playbook on similar systems"""
        try:
            # Search for execution records of this playbook
            search_results = await self.memory_storage.search_memories(
                query=f"playbook_id:{playbook_id} execution",
                category="deployments",
                limit=100
            )
            
            total_executions = 0
            successful_executions = 0
            
            for memory in search_results.get('memories', []):
                content = memory.get('content', '').lower()
                if 'success' in content or 'completed' in content:
                    successful_executions += 1
                total_executions += 1
            
            if total_executions == 0:
                return 0.7  # Default optimistic score for untested playbooks
            
            return successful_executions / total_executions
            
        except Exception as e:
            logger.warning(f"Failed to get historical success rate: {e}")
            return 0.7
    
    def _calculate_confidence_score(self, 
                                  playbook: Dict[str, Any], 
                                  relevance_score: float,
                                  agent_context: Optional[Dict[str, Any]]) -> float:
        """Calculate confidence score for the recommendation"""
        base_confidence = relevance_score
        
        # Boost confidence for manual playbooks
        if playbook.get('type') == 'manual':
            base_confidence *= 1.1
        
        # Boost confidence if auto-generated playbook has high pattern confidence
        if playbook.get('type') == 'auto_generated':
            pattern_confidence = playbook.get('metadata', {}).get('confidence_score', 0.5)
            base_confidence = (base_confidence + pattern_confidence) / 2
        
        # Adjust based on agent expertise
        if agent_context:
            agent_capabilities = agent_context.get('capabilities', [])
            playbook_systems = self._extract_systems_from_content(playbook.get('content', ''))
            
            expertise_match = len(set(agent_capabilities) & set(playbook_systems)) / max(len(playbook_systems), 1)
            base_confidence += expertise_match * 0.1
        
        return min(base_confidence, 1.0)
    
    def _generate_reasoning(self, 
                          text_sim: float, 
                          system_match: float, 
                          severity_match: float,
                          symptom_match: float, 
                          historical_success: float) -> List[str]:
        """Generate human-readable reasoning for the recommendation"""
        reasoning = []
        
        if text_sim > 0.7:
            reasoning.append(f"High text similarity ({text_sim:.1%}) with incident description")
        elif text_sim > 0.4:
            reasoning.append(f"Moderate text similarity ({text_sim:.1%}) with incident description")
        
        if system_match > 0.8:
            reasoning.append("Exact match for affected systems")
        elif system_match > 0.5:
            reasoning.append("Partial match for affected systems")
        
        if severity_match > 0.8:
            reasoning.append("Appropriate for incident severity level")
        
        if symptom_match > 0.6:
            reasoning.append("Addresses reported symptoms")
        
        if historical_success > 0.8:
            reasoning.append(f"High historical success rate ({historical_success:.1%})")
        elif historical_success > 0.6:
            reasoning.append(f"Good historical success rate ({historical_success:.1%})")
        
        if not reasoning:
            reasoning.append("General applicability to incident type")
        
        return reasoning
    
    def _estimate_duration(self, playbook_content: str) -> int:
        """Estimate playbook execution duration in minutes"""
        # Count steps and estimate time per step
        step_count = len(re.findall(r'step|action|procedure', playbook_content.lower()))
        
        # Base time estimates
        if 'restart' in playbook_content.lower():
            base_time = 10  # Restart operations
        elif 'deploy' in playbook_content.lower():
            base_time = 30  # Deployment operations
        elif 'backup' in playbook_content.lower():
            base_time = 60  # Backup operations
        else:
            base_time = 5   # General operations
        
        return max(step_count * base_time, 5)  # Minimum 5 minutes
    
    def _extract_required_permissions(self, playbook_content: str) -> List[str]:
        """Extract required permissions from playbook content"""
        permissions = []
        content_lower = playbook_content.lower()
        
        if 'sudo' in content_lower or 'root' in content_lower:
            permissions.append('sudo')
        if 'docker' in content_lower:
            permissions.append('docker')
        if 'kubectl' in content_lower or 'kubernetes' in content_lower:
            permissions.append('kubernetes')
        if 'systemctl' in content_lower:
            permissions.append('systemd')
        
        return permissions
    
    def _extract_prerequisites(self, playbook_content: str) -> List[str]:
        """Extract prerequisites from playbook content"""
        prerequisites = []
        
        # Look for explicit prerequisites section
        prereq_match = re.search(r'prerequisite[s]?:?\s*(.+?)(?:\n\n|\n[A-Z]|$)', 
                                playbook_content, re.IGNORECASE | re.DOTALL)
        if prereq_match:
            prereq_text = prereq_match.group(1)
            # Split by lines and clean up
            for line in prereq_text.split('\n'):
                line = line.strip('- ').strip()
                if line and len(line) > 5:
                    prerequisites.append(line)
        
        # Look for common prerequisite patterns
        content_lower = playbook_content.lower()
        if 'backup' in content_lower:
            prerequisites.append('Ensure recent backup exists')
        if 'maintenance' in content_lower:
            prerequisites.append('Schedule maintenance window')
        if 'cluster' in content_lower:
            prerequisites.append('Verify cluster health')
        
        return prerequisites[:5]  # Limit to top 5
    
    def _extract_description(self, playbook_content: str) -> str:
        """Extract a brief description from playbook content"""
        # Look for description section
        desc_match = re.search(r'description:?\s*(.+?)(?:\n\n|\n[A-Z]|$)', 
                              playbook_content, re.IGNORECASE)
        if desc_match:
            return desc_match.group(1).strip()
        
        # Fallback to first meaningful line
        lines = playbook_content.split('\n')
        for line in lines:
            line = line.strip()
            if len(line) > 20 and not line.startswith('#'):
                return line[:200] + "..." if len(line) > 200 else line
        
        return "Automated procedure for incident resolution"
    
    def _extract_systems_from_content(self, content: str) -> List[str]:
        """Extract system names from content"""
        systems = []
        content_lower = content.lower()
        
        system_patterns = [
            'elasticsearch', 'nginx', 'apache', 'mysql', 'postgresql', 
            'redis', 'docker', 'kubernetes', 'jenkins', 'grafana'
        ]
        
        for system in system_patterns:
            if system in content_lower:
                systems.append(system)
        
        return systems
    
    async def _find_similar_incidents(self, incident_context: IncidentContext) -> List[str]:
        """Find similar historical incidents"""
        try:
            # Search for similar incidents
            search_query = f"{incident_context.title} {' '.join(incident_context.symptoms[:3])}"
            
            search_results = await self.memory_storage.search_memories(
                query=search_query,
                category="incidents",
                limit=10
            )
            
            similar_incidents = []
            for memory in search_results.get('memories', []):
                incident_id = memory.get('id')
                if incident_id != incident_context.incident_id:
                    similar_incidents.append(incident_id)
            
            return similar_incidents[:5]  # Return top 5
            
        except Exception as e:
            logger.warning(f"Failed to find similar incidents: {e}")
            return []
    
    async def _enhance_recommendations(self, 
                                     recommendations: List[PlaybookRecommendation],
                                     incident_context: IncidentContext) -> List[PlaybookRecommendation]:
        """Enhance recommendations with additional context and validation"""
        try:
            enhanced = []
            
            for rec in recommendations:
                # Add real-time context
                rec = await self._add_realtime_context(rec, incident_context)
                
                # Validate prerequisites
                rec = await self._validate_prerequisites(rec)
                
                # Add agent availability info
                rec = await self._add_agent_availability(rec)
                
                enhanced.append(rec)
            
            return enhanced
            
        except Exception as e:
            logger.error(f"Failed to enhance recommendations: {e}")
            return recommendations
    
    async def _add_realtime_context(self, 
                                   recommendation: PlaybookRecommendation,
                                   incident_context: IncidentContext) -> PlaybookRecommendation:
        """Add real-time monitoring context to recommendation"""
        try:
            # Check current system status
            if hasattr(self.memory_storage, 'track_infrastructure_state'):
                for system in incident_context.affected_systems:
                    # This would integrate with monitoring systems
                    # For now, we'll add a placeholder
                    recommendation.reasoning.append(f"Real-time monitoring available for {system}")
            
            return recommendation
            
        except Exception as e:
            logger.warning(f"Failed to add real-time context: {e}")
            return recommendation
    
    async def _validate_prerequisites(self, recommendation: PlaybookRecommendation) -> PlaybookRecommendation:
        """Validate that prerequisites are met"""
        try:
            # Check if required permissions are available
            # This would integrate with authentication/authorization systems
            # For now, we'll add validation notes
            
            if 'sudo' in recommendation.required_permissions:
                recommendation.reasoning.append("Requires elevated privileges")
            
            return recommendation
            
        except Exception as e:
            logger.warning(f"Failed to validate prerequisites: {e}")
            return recommendation
    
    async def _add_agent_availability(self, recommendation: PlaybookRecommendation) -> PlaybookRecommendation:
        """Add information about agent availability for execution"""
        try:
            # Check for agents with relevant capabilities
            if hasattr(self.memory_storage, 'get_agent_roster'):
                agents = await self.memory_storage.get_agent_roster()
                
                capable_agents = []
                for agent in agents.get('agents', []):
                    agent_capabilities = agent.get('capabilities', [])
                    if any(cap in agent_capabilities for cap in recommendation.affected_systems):
                        capable_agents.append(agent.get('agent_id'))
                
                if capable_agents:
                    recommendation.reasoning.append(f"Available agents: {', '.join(capable_agents[:3])}")
            
            return recommendation
            
        except Exception as e:
            logger.warning(f"Failed to add agent availability: {e}")
            return recommendation
    
    async def recommend_for_current_context(self, 
                                          query: str,
                                          systems: Optional[List[str]] = None,
                                          severity: str = "medium") -> List[PlaybookRecommendation]:
        """Recommend playbooks for current operational context"""
        try:
            # Create incident context from query
            incident_context = IncidentContext(
                incident_id=f"context_{int(time.time())}",
                title=query,
                description=query,
                affected_systems=systems or [],
                severity=severity,
                symptoms=[query],
                error_messages=[],
                monitoring_alerts=[],
                duration_minutes=0,
                reporter="system",
                current_status="investigating"
            )
            
            # Get recommendations
            recommendations = await self.recommend_playbooks(incident_context)
            
            logger.info(f"🎯 Generated {len(recommendations)} contextual recommendations")
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate contextual recommendations: {e}")
            return []
    
    async def get_recommendation_feedback(self, 
                                        recommendation_id: str,
                                        executed: bool,
                                        successful: bool,
                                        feedback_notes: Optional[str] = None) -> bool:
        """Record feedback on recommendation effectiveness"""
        try:
            feedback_data = {
                "recommendation_id": recommendation_id,
                "executed": executed,
                "successful": successful,
                "feedback_notes": feedback_notes,
                "timestamp": datetime.now().isoformat(),
                "agent_id": self.memory_storage.agent_id
            }
            
            # Store feedback in memory system
            await self.memory_storage.store_memory(
                content=json.dumps(feedback_data),
                category="recommendation_feedback",
                metadata={
                    "recommendation_id": recommendation_id,
                    "executed": executed,
                    "successful": successful,
                    "feedback_type": "recommendation_effectiveness"
                }
            )
            
            logger.info(f"📝 Recorded recommendation feedback: {recommendation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to record recommendation feedback: {e}")
            return False