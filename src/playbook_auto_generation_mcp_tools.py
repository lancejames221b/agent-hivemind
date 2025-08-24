#!/usr/bin/env python3
"""
MCP Tools for Playbook Auto-Generation System

This module provides MCP tools for the intelligent playbook auto-generation system:
- Pattern analysis and detection from incident memories
- Auto-generation of playbooks from successful resolution patterns
- Human review workflow for generated playbooks
- Recommendation engine for contextual playbook suggestions
- Integration with hAIveMind for cross-agent learning
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from playbook_auto_generator import PlaybookAutoGenerator, IncidentContext
from playbook_recommendation_engine import PlaybookRecommendationEngine

logger = logging.getLogger(__name__)

class PlaybookAutoGenerationMCPTools:
    """MCP tools for intelligent playbook auto-generation"""
    
    def __init__(self, memory_storage, config: Dict[str, Any]):
        self.memory_storage = memory_storage
        self.config = config
        
        # Initialize core components
        self.auto_generator = PlaybookAutoGenerator(memory_storage, config.get('auto_generation', {}))
        self.recommendation_engine = PlaybookRecommendationEngine(
            memory_storage, self.auto_generator, config.get('recommendations', {})
        )
        
        # Background task for continuous monitoring
        self._monitoring_task = None
        self._start_continuous_monitoring()
    
    def _start_continuous_monitoring(self):
        """Start continuous pattern monitoring in background"""
        try:
            if self.config.get('auto_generation', {}).get('continuous_monitoring', True):
                interval_hours = self.config.get('auto_generation', {}).get('monitoring_interval_hours', 24)
                self._monitoring_task = asyncio.create_task(
                    self.auto_generator.continuous_pattern_monitoring(interval_hours)
                )
                logger.info(f"🔄 Started continuous pattern monitoring (every {interval_hours} hours)")
        except Exception as e:
            logger.error(f"Failed to start continuous monitoring: {e}")
    
    async def analyze_incident_patterns(self, 
                                      lookback_days: int = 30,
                                      min_incidents: int = 5,
                                      force_analysis: bool = False) -> Dict[str, Any]:
        """
        Analyze incident patterns and generate playbook suggestions
        
        Args:
            lookback_days: Number of days to analyze (default: 30)
            min_incidents: Minimum incidents needed for pattern detection (default: 5)
            force_analysis: Force analysis even if recent analysis exists (default: False)
            
        Returns:
            Analysis results with patterns and suggestions
        """
        try:
            logger.info(f"🔍 Starting incident pattern analysis (lookback: {lookback_days} days)")
            
            # Check if recent analysis exists (unless forced)
            if not force_analysis:
                recent_analysis = await self._check_recent_analysis(hours=6)
                if recent_analysis:
                    return {
                        "status": "recent_analysis_exists",
                        "message": "Recent analysis found, use force_analysis=true to override",
                        "last_analysis": recent_analysis,
                        "patterns_found": 0,
                        "suggestions_generated": 0
                    }
            
            # Run pattern analysis
            result = await self.auto_generator.analyze_incident_patterns(
                lookback_days=lookback_days,
                min_incidents=min_incidents
            )
            
            # Format response
            response = {
                "status": "completed",
                "analysis_date": datetime.now().isoformat(),
                "patterns_found": len(result.patterns_found),
                "new_patterns": len(result.new_patterns),
                "updated_patterns": len(result.updated_patterns),
                "suggestions_generated": len(result.playbook_suggestions),
                "metadata": result.analysis_metadata
            }
            
            # Add pattern summaries
            if result.new_patterns:
                response["new_pattern_summary"] = [
                    {
                        "pattern_id": p.pattern_id,
                        "incident_type": p.incident_type,
                        "frequency": p.frequency,
                        "success_rate": p.success_rate,
                        "systems": p.common_systems[:3]
                    }
                    for p in result.new_patterns[:5]
                ]
            
            # Add suggestion summaries
            if result.playbook_suggestions:
                response["suggestion_summary"] = [
                    {
                        "suggestion_id": s.suggestion_id,
                        "title": s.title,
                        "confidence_score": s.confidence_score,
                        "pattern_id": s.pattern_id,
                        "review_status": s.human_review_status
                    }
                    for s in result.playbook_suggestions[:5]
                ]
            
            logger.info(f"✅ Pattern analysis completed: {response['patterns_found']} patterns, {response['suggestions_generated']} suggestions")
            return response
            
        except Exception as e:
            logger.error(f"💥 Pattern analysis failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "patterns_found": 0,
                "suggestions_generated": 0
            }
    
    async def _check_recent_analysis(self, hours: int = 6) -> Optional[Dict[str, Any]]:
        """Check if recent pattern analysis exists"""
        try:
            cutoff = datetime.now() - timedelta(hours=hours)
            
            search_results = await self.memory_storage.search_memories(
                query="pattern analysis completed",
                category="patterns",
                limit=1
            )
            
            for memory in search_results.get('memories', []):
                try:
                    timestamp = datetime.fromisoformat(memory.get('timestamp', '').replace('Z', '+00:00'))
                    if timestamp >= cutoff:
                        return {
                            "timestamp": memory.get('timestamp'),
                            "analysis_id": memory.get('id')
                        }
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to check recent analysis: {e}")
            return None
    
    async def get_pending_playbook_suggestions(self, limit: int = 20) -> Dict[str, Any]:
        """
        Get pending playbook suggestions for human review
        
        Args:
            limit: Maximum number of suggestions to return (default: 20)
            
        Returns:
            List of pending suggestions with details
        """
        try:
            suggestions = await self.auto_generator.get_pending_suggestions(limit)
            
            suggestion_list = []
            for suggestion in suggestions:
                suggestion_data = {
                    "suggestion_id": suggestion.suggestion_id,
                    "title": suggestion.title,
                    "description": suggestion.description,
                    "confidence_score": suggestion.confidence_score,
                    "pattern_id": suggestion.pattern_id,
                    "created_at": suggestion.created_at.isoformat(),
                    "playbook_preview": self._create_playbook_preview(suggestion.playbook_spec)
                }
                suggestion_list.append(suggestion_data)
            
            return {
                "status": "success",
                "pending_suggestions": len(suggestion_list),
                "suggestions": suggestion_list
            }
            
        except Exception as e:
            logger.error(f"Failed to get pending suggestions: {e}")
            return {
                "status": "error",
                "error": str(e),
                "pending_suggestions": 0,
                "suggestions": []
            }
    
    def _create_playbook_preview(self, playbook_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Create a preview of the playbook specification"""
        return {
            "name": playbook_spec.get('name', 'Unknown'),
            "description": playbook_spec.get('description', ''),
            "step_count": len(playbook_spec.get('steps', [])),
            "parameters": len(playbook_spec.get('parameters', [])),
            "category": playbook_spec.get('category', 'auto-generated')
        }
    
    async def review_playbook_suggestion(self, 
                                       suggestion_id: str,
                                       action: str,
                                       reviewer_notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Review a playbook suggestion (approve, reject, or request revision)
        
        Args:
            suggestion_id: ID of the suggestion to review
            action: Review action ("approve", "reject", "needs_revision")
            reviewer_notes: Optional notes from reviewer
            
        Returns:
            Review result and next steps
        """
        try:
            if action not in ["approve", "reject", "needs_revision"]:
                return {
                    "status": "error",
                    "error": "Invalid action. Must be 'approve', 'reject', or 'needs_revision'"
                }
            
            # Perform the review
            success = await self.auto_generator.review_suggestion(
                suggestion_id=suggestion_id,
                status=action,
                reviewer_notes=reviewer_notes
            )
            
            if not success:
                return {
                    "status": "error",
                    "error": "Suggestion not found or review failed"
                }
            
            response = {
                "status": "success",
                "suggestion_id": suggestion_id,
                "action": action,
                "reviewed_at": datetime.now().isoformat()
            }
            
            if action == "approve":
                response["message"] = "Suggestion approved and playbook created"
                response["next_steps"] = "Playbook is now available for execution"
            elif action == "reject":
                response["message"] = "Suggestion rejected"
                response["next_steps"] = "Suggestion will not be converted to playbook"
            else:  # needs_revision
                response["message"] = "Suggestion marked for revision"
                response["next_steps"] = "Suggestion will be refined in next analysis cycle"
            
            logger.info(f"✅ Reviewed suggestion {suggestion_id}: {action}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to review suggestion: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def recommend_playbooks_for_incident(self, 
                                             incident_title: str,
                                             incident_description: str,
                                             affected_systems: Optional[List[str]] = None,
                                             severity: str = "medium",
                                             symptoms: Optional[List[str]] = None,
                                             include_auto_generated: bool = True) -> Dict[str, Any]:
        """
        Get playbook recommendations for a specific incident
        
        Args:
            incident_title: Title of the incident
            incident_description: Detailed description
            affected_systems: List of affected systems
            severity: Incident severity ("low", "medium", "high", "critical")
            symptoms: List of observed symptoms
            include_auto_generated: Include auto-generated playbooks
            
        Returns:
            Recommended playbooks with relevance scores
        """
        try:
            # Create incident context
            incident_context = IncidentContext(
                incident_id=f"incident_{int(datetime.now().timestamp())}",
                title=incident_title,
                description=incident_description,
                affected_systems=affected_systems or [],
                severity=severity,
                symptoms=symptoms or [],
                error_messages=[],
                monitoring_alerts=[],
                duration_minutes=0,
                reporter=self.memory_storage.agent_id,
                current_status="investigating"
            )
            
            # Get recommendations
            recommendations = await self.recommendation_engine.recommend_playbooks(
                incident_context=incident_context,
                include_auto_generated=include_auto_generated
            )
            
            # Format recommendations
            recommendation_list = []
            for rec in recommendations:
                rec_data = {
                    "playbook_id": rec.playbook_id,
                    "title": rec.title,
                    "description": rec.description,
                    "relevance_score": rec.relevance_score,
                    "confidence_score": rec.confidence_score,
                    "reasoning": rec.reasoning,
                    "estimated_duration_minutes": rec.estimated_duration,
                    "required_permissions": rec.required_permissions,
                    "prerequisites": rec.prerequisites,
                    "success_probability": rec.success_probability,
                    "recommended_by": rec.recommended_by
                }
                recommendation_list.append(rec_data)
            
            return {
                "status": "success",
                "incident_context": {
                    "title": incident_title,
                    "severity": severity,
                    "affected_systems": affected_systems or [],
                    "symptoms": symptoms or []
                },
                "recommendations_count": len(recommendation_list),
                "recommendations": recommendation_list
            }
            
        except Exception as e:
            logger.error(f"Failed to get incident recommendations: {e}")
            return {
                "status": "error",
                "error": str(e),
                "recommendations_count": 0,
                "recommendations": []
            }
    
    async def recommend_playbooks_for_context(self, 
                                            query: str,
                                            systems: Optional[List[str]] = None,
                                            severity: str = "medium") -> Dict[str, Any]:
        """
        Get playbook recommendations for current operational context
        
        Args:
            query: Description of current situation or need
            systems: Relevant systems (optional)
            severity: Context severity level
            
        Returns:
            Contextual playbook recommendations
        """
        try:
            recommendations = await self.recommendation_engine.recommend_for_current_context(
                query=query,
                systems=systems,
                severity=severity
            )
            
            # Format recommendations
            recommendation_list = []
            for rec in recommendations:
                rec_data = {
                    "playbook_id": rec.playbook_id,
                    "title": rec.title,
                    "description": rec.description,
                    "relevance_score": rec.relevance_score,
                    "confidence_score": rec.confidence_score,
                    "reasoning": rec.reasoning,
                    "estimated_duration_minutes": rec.estimated_duration,
                    "prerequisites": rec.prerequisites
                }
                recommendation_list.append(rec_data)
            
            return {
                "status": "success",
                "query": query,
                "context": {
                    "systems": systems or [],
                    "severity": severity
                },
                "recommendations_count": len(recommendation_list),
                "recommendations": recommendation_list
            }
            
        except Exception as e:
            logger.error(f"Failed to get contextual recommendations: {e}")
            return {
                "status": "error",
                "error": str(e),
                "recommendations_count": 0,
                "recommendations": []
            }
    
    async def get_pattern_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about detected patterns and auto-generation performance
        
        Returns:
            Statistics about patterns, suggestions, and system performance
        """
        try:
            stats = await self.auto_generator.get_pattern_statistics()
            
            # Add recommendation engine stats
            if hasattr(self.recommendation_engine, 'get_statistics'):
                rec_stats = await self.recommendation_engine.get_statistics()
                stats.update(rec_stats)
            
            # Add system health info
            stats["system_health"] = {
                "continuous_monitoring_active": self._monitoring_task is not None and not self._monitoring_task.done(),
                "last_update": datetime.now().isoformat(),
                "memory_storage_connected": hasattr(self.memory_storage, 'chroma_client')
            }
            
            return {
                "status": "success",
                "statistics": stats
            }
            
        except Exception as e:
            logger.error(f"Failed to get pattern statistics: {e}")
            return {
                "status": "error",
                "error": str(e),
                "statistics": {}
            }
    
    async def record_recommendation_feedback(self, 
                                           recommendation_id: str,
                                           executed: bool,
                                           successful: bool,
                                           feedback_notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Record feedback on recommendation effectiveness for learning
        
        Args:
            recommendation_id: ID of the recommendation
            executed: Whether the recommendation was executed
            successful: Whether execution was successful (if executed)
            feedback_notes: Additional feedback notes
            
        Returns:
            Confirmation of feedback recording
        """
        try:
            success = await self.recommendation_engine.get_recommendation_feedback(
                recommendation_id=recommendation_id,
                executed=executed,
                successful=successful,
                feedback_notes=feedback_notes
            )
            
            if success:
                return {
                    "status": "success",
                    "message": "Feedback recorded successfully",
                    "recommendation_id": recommendation_id,
                    "recorded_at": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "error": "Failed to record feedback"
                }
            
        except Exception as e:
            logger.error(f"Failed to record recommendation feedback: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def trigger_pattern_learning(self, 
                                     incident_memories: Optional[List[str]] = None,
                                     force_reanalysis: bool = False) -> Dict[str, Any]:
        """
        Manually trigger pattern learning from specific incidents or all recent incidents
        
        Args:
            incident_memories: Specific incident memory IDs to analyze (optional)
            force_reanalysis: Force reanalysis of already processed incidents
            
        Returns:
            Learning results and new patterns discovered
        """
        try:
            if incident_memories:
                # Analyze specific incidents
                logger.info(f"🎯 Triggering pattern learning for {len(incident_memories)} specific incidents")
                # This would require extending the auto_generator to handle specific incidents
                return {
                    "status": "not_implemented",
                    "message": "Specific incident analysis not yet implemented",
                    "suggestion": "Use analyze_incident_patterns for general analysis"
                }
            else:
                # Analyze recent incidents
                result = await self.auto_generator.analyze_incident_patterns(
                    lookback_days=7,  # Focus on recent incidents
                    min_incidents=2,  # Lower threshold for manual trigger
                )
                
                return {
                    "status": "success",
                    "message": "Pattern learning completed",
                    "patterns_found": len(result.patterns_found),
                    "new_patterns": len(result.new_patterns),
                    "suggestions_generated": len(result.playbook_suggestions),
                    "analysis_metadata": result.analysis_metadata
                }
            
        except Exception as e:
            logger.error(f"Failed to trigger pattern learning: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def export_generated_playbooks(self, 
                                       format: str = "json",
                                       include_pending: bool = False) -> Dict[str, Any]:
        """
        Export auto-generated playbooks for backup or external use
        
        Args:
            format: Export format ("json", "yaml") 
            include_pending: Include pending suggestions
            
        Returns:
            Exported playbook data
        """
        try:
            # Get approved playbooks
            approved_search = await self.memory_storage.search_memories(
                query="human_review_status:approved",
                category="playbook_suggestions",
                limit=1000
            )
            
            playbooks = []
            for memory in approved_search.get('memories', []):
                try:
                    suggestion_data = json.loads(memory.get('content', '{}'))
                    if suggestion_data.get('human_review_status') == 'approved':
                        playbook_export = {
                            "id": suggestion_data.get('suggestion_id'),
                            "title": suggestion_data.get('title'),
                            "description": suggestion_data.get('description'),
                            "confidence_score": suggestion_data.get('confidence_score'),
                            "pattern_id": suggestion_data.get('pattern_id'),
                            "playbook_spec": suggestion_data.get('playbook_spec'),
                            "created_at": suggestion_data.get('created_at'),
                            "reviewed_at": suggestion_data.get('reviewed_at')
                        }
                        playbooks.append(playbook_export)
                except Exception as e:
                    logger.warning(f"Failed to export playbook: {e}")
            
            # Include pending if requested
            if include_pending:
                pending_suggestions = await self.auto_generator.get_pending_suggestions(100)
                for suggestion in pending_suggestions:
                    playbook_export = {
                        "id": suggestion.suggestion_id,
                        "title": suggestion.title,
                        "description": suggestion.description,
                        "confidence_score": suggestion.confidence_score,
                        "pattern_id": suggestion.pattern_id,
                        "playbook_spec": suggestion.playbook_spec,
                        "created_at": suggestion.created_at.isoformat(),
                        "status": "pending_review"
                    }
                    playbooks.append(playbook_export)
            
            export_data = {
                "export_metadata": {
                    "exported_at": datetime.now().isoformat(),
                    "format": format,
                    "total_playbooks": len(playbooks),
                    "include_pending": include_pending,
                    "exported_by": self.memory_storage.agent_id
                },
                "playbooks": playbooks
            }
            
            if format == "yaml":
                try:
                    import yaml
                    yaml_content = yaml.dump(export_data, default_flow_style=False)
                    return {
                        "status": "success",
                        "format": "yaml",
                        "content": yaml_content,
                        "playbooks_exported": len(playbooks)
                    }
                except ImportError:
                    return {
                        "status": "error",
                        "error": "YAML export requires PyYAML package"
                    }
            else:
                return {
                    "status": "success",
                    "format": "json",
                    "content": json.dumps(export_data, indent=2, default=str),
                    "playbooks_exported": len(playbooks)
                }
            
        except Exception as e:
            logger.error(f"Failed to export playbooks: {e}")
            return {
                "status": "error",
                "error": str(e),
                "playbooks_exported": 0
            }
    
    def cleanup(self):
        """Cleanup background tasks"""
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            logger.info("🛑 Stopped continuous pattern monitoring")