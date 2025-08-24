#!/usr/bin/env python3
"""
hAIveMind Rules Integration - Enhanced Memory and Network Awareness
Integrates rules management with hAIveMind memory system for learning and collaboration

Author: Lance James, Unit 221B Inc
"""

import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import logging

from .rule_management_service import RuleManagementService
from .rules_engine import Rule, RuleType, RuleScope, RulePriority, RuleStatus

logger = logging.getLogger(__name__)

@dataclass
class RuleMemoryEntry:
    """Memory entry for rule-related operations"""
    id: str
    rule_id: str
    operation_type: str  # created, updated, evaluated, optimized, conflicted
    context: Dict[str, Any]
    outcome: Dict[str, Any]
    learning_data: Dict[str, Any]
    agent_id: str
    machine_id: str
    timestamp: datetime
    metadata: Dict[str, Any] = None

@dataclass
class RuleEffectivenessMetric:
    """Metric for measuring rule effectiveness"""
    rule_id: str
    success_count: int
    failure_count: int
    avg_execution_time: float
    effectiveness_score: float
    last_evaluated: datetime
    recommendations: List[str]

@dataclass
class RuleInsight:
    """Insight discovered about rule usage"""
    insight_id: str
    rule_id: str
    insight_type: str  # pattern, anomaly, optimization, conflict
    description: str
    data: Dict[str, Any]
    confidence: float
    discovered_at: datetime
    suggested_actions: List[str]

class RulesHAIveMindIntegration:
    """Enhanced integration between Rules Engine and hAIveMind memory system"""
    
    def __init__(self, rule_service: RuleManagementService, memory_client=None, redis_client=None):
        self.rule_service = rule_service
        self.memory_client = memory_client
        self.redis_client = redis_client
        self.machine_id = "lance-dev"  # TODO: Get from config
        
    def store_rule_operation_memory(self, rule_id: str, operation_type: str,
                                   context: Dict[str, Any], outcome: Dict[str, Any],
                                   agent_id: str, learning_data: Optional[Dict[str, Any]] = None):
        """Store rule operation as memory for learning and audit"""
        if not self.memory_client:
            return
        
        memory_entry = RuleMemoryEntry(
            id=str(uuid.uuid4()),
            rule_id=rule_id,
            operation_type=operation_type,
            context=context,
            outcome=outcome,
            learning_data=learning_data or {},
            agent_id=agent_id,
            machine_id=self.machine_id,
            timestamp=datetime.now()
        )
        
        try:
            # Store as structured memory
            self.memory_client.store_memory(
                content=f"Rule {operation_type}: {rule_id}",
                category="rules",
                project_id=context.get('project_id'),
                metadata={
                    "rule_operation": asdict(memory_entry),
                    "sharing_scope": "network-shared",
                    "importance": self._calculate_operation_importance(operation_type, outcome),
                    "tags": ["rules", "governance", operation_type, rule_id[:8]]
                }
            )
            
            # Broadcast to hAIveMind network
            if self.redis_client:
                self._broadcast_rule_operation(memory_entry)
            
        except Exception as e:
            logger.error(f"Failed to store rule operation memory: {e}")
    
    def analyze_rule_effectiveness(self, rule_id: str, days: int = 30) -> RuleEffectivenessMetric:
        """Analyze rule effectiveness based on historical data"""
        if not self.memory_client:
            return self._default_effectiveness_metric(rule_id)
        
        try:
            # Search for rule evaluation memories
            search_results = self.memory_client.search_memories(
                query=f"rule_id:{rule_id}",
                filters={
                    "category": "rules",
                    "created_after": datetime.now() - timedelta(days=days)
                },
                limit=1000
            )
            
            success_count = 0
            failure_count = 0
            total_execution_time = 0
            evaluation_count = 0
            
            for memory in search_results:
                rule_data = memory.get('metadata', {}).get('rule_operation', {})
                if rule_data.get('operation_type') == 'evaluated':
                    evaluation_count += 1
                    outcome = rule_data.get('outcome', {})
                    
                    if outcome.get('success', False):
                        success_count += 1
                    else:
                        failure_count += 1
                    
                    execution_time = outcome.get('execution_time_ms', 0)
                    total_execution_time += execution_time
            
            # Calculate metrics
            avg_execution_time = total_execution_time / max(evaluation_count, 1)
            total_evaluations = success_count + failure_count
            effectiveness_score = success_count / max(total_evaluations, 1) if total_evaluations > 0 else 0.0
            
            # Generate recommendations
            recommendations = self._generate_effectiveness_recommendations(
                effectiveness_score, avg_execution_time, total_evaluations
            )
            
            return RuleEffectivenessMetric(
                rule_id=rule_id,
                success_count=success_count,
                failure_count=failure_count,
                avg_execution_time=avg_execution_time,
                effectiveness_score=effectiveness_score,
                last_evaluated=datetime.now(),
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Failed to analyze rule effectiveness: {e}")
            return self._default_effectiveness_metric(rule_id)
    
    def discover_rule_patterns(self, agent_id: Optional[str] = None, 
                              days: int = 14) -> List[RuleInsight]:
        """Discover patterns in rule usage across the network"""
        if not self.memory_client:
            return []
        
        insights = []
        
        try:
            # Search for recent rule memories
            search_query = "rules governance"
            if agent_id:
                search_query += f" agent:{agent_id}"
            
            search_results = self.memory_client.search_memories(
                query=search_query,
                filters={
                    "category": "rules",
                    "created_after": datetime.now() - timedelta(days=days)
                },
                limit=500
            )
            
            # Analyze patterns
            rule_usage = {}
            operation_patterns = {}
            failure_patterns = {}
            
            for memory in search_results:
                rule_data = memory.get('metadata', {}).get('rule_operation', {})
                rule_id = rule_data.get('rule_id')
                operation_type = rule_data.get('operation_type')
                outcome = rule_data.get('outcome', {})
                
                if rule_id:
                    # Track usage frequency
                    rule_usage[rule_id] = rule_usage.get(rule_id, 0) + 1
                    
                    # Track operation patterns
                    key = f"{operation_type}:{rule_id}"
                    operation_patterns[key] = operation_patterns.get(key, 0) + 1
                    
                    # Track failures
                    if not outcome.get('success', True):
                        failure_key = f"{rule_id}:{outcome.get('error_type', 'unknown')}"
                        failure_patterns[failure_key] = failure_patterns.get(failure_key, 0) + 1
            
            # Generate insights from patterns
            
            # High-usage rules
            high_usage_threshold = max(rule_usage.values()) * 0.8 if rule_usage else 0
            for rule_id, count in rule_usage.items():
                if count >= high_usage_threshold and count > 5:
                    insights.append(RuleInsight(
                        insight_id=str(uuid.uuid4()),
                        rule_id=rule_id,
                        insight_type="pattern",
                        description=f"Rule {rule_id} has high usage ({count} times in {days} days)",
                        data={"usage_count": count, "usage_frequency": count/days},
                        confidence=0.9,
                        discovered_at=datetime.now(),
                        suggested_actions=["Consider optimizing for performance", "Review rule complexity"]
                    ))
            
            # Frequent failures
            for failure_key, count in failure_patterns.items():
                if count > 3:  # More than 3 failures
                    rule_id, error_type = failure_key.split(':', 1)
                    insights.append(RuleInsight(
                        insight_id=str(uuid.uuid4()),
                        rule_id=rule_id,
                        insight_type="anomaly",
                        description=f"Rule {rule_id} frequently fails with {error_type}",
                        data={"failure_count": count, "error_type": error_type},
                        confidence=0.8,
                        discovered_at=datetime.now(),
                        suggested_actions=["Review rule conditions", "Update rule logic", "Check context requirements"]
                    ))
            
            # Store insights as memories
            for insight in insights:
                self.memory_client.store_memory(
                    content=f"Rule Insight: {insight.description}",
                    category="rules",
                    metadata={
                        "insight_data": asdict(insight),
                        "sharing_scope": "network-shared",
                        "importance": "high" if insight.confidence > 0.8 else "medium",
                        "tags": ["insights", "patterns", "rules", insight.insight_type]
                    }
                )
            
        except Exception as e:
            logger.error(f"Failed to discover rule patterns: {e}")
        
        return insights
    
    def recommend_rule_improvements(self, rule_id: str) -> List[Dict[str, Any]]:
        """Generate AI-powered recommendations for rule improvements"""
        recommendations = []
        
        # Get rule effectiveness
        effectiveness = self.analyze_rule_effectiveness(rule_id)
        
        # Get rule details
        rule = self.rule_service.db.get_rule(rule_id)
        if not rule:
            return recommendations
        
        # Performance recommendations
        if effectiveness.avg_execution_time > 100:  # >100ms
            recommendations.append({
                "type": "performance",
                "priority": "high",
                "title": "Optimize Rule Performance",
                "description": f"Rule execution time ({effectiveness.avg_execution_time:.1f}ms) is above optimal threshold",
                "suggested_actions": [
                    "Simplify complex conditions",
                    "Reduce number of regex operations",
                    "Add condition ordering for short-circuit evaluation"
                ],
                "impact_estimate": "20-50% performance improvement"
            })
        
        # Effectiveness recommendations
        if effectiveness.effectiveness_score < 0.7:  # Less than 70% success rate
            recommendations.append({
                "type": "effectiveness",
                "priority": "high",
                "title": "Improve Rule Success Rate",
                "description": f"Rule success rate ({effectiveness.effectiveness_score:.1%}) is below expectations",
                "suggested_actions": [
                    "Review and update rule conditions",
                    "Add fallback actions for edge cases",
                    "Improve error handling in actions"
                ],
                "impact_estimate": "Potential 15-30% improvement in success rate"
            })
        
        # Usage-based recommendations
        if effectiveness.success_count + effectiveness.failure_count == 0:
            recommendations.append({
                "type": "usage",
                "priority": "medium",
                "title": "Unused Rule Detected",
                "description": "Rule has not been evaluated recently",
                "suggested_actions": [
                    "Review rule relevance",
                    "Update rule conditions to match current context",
                    "Consider archiving if no longer needed"
                ],
                "impact_estimate": "Improved system efficiency"
            })
        
        # Complexity recommendations
        condition_count = len(rule.conditions)
        action_count = len(rule.actions)
        
        if condition_count > 5 or action_count > 3:
            recommendations.append({
                "type": "complexity",
                "priority": "medium",
                "title": "Reduce Rule Complexity",
                "description": f"Rule has {condition_count} conditions and {action_count} actions",
                "suggested_actions": [
                    "Split into multiple focused rules",
                    "Simplify complex conditions",
                    "Use rule dependencies instead of complex single rules"
                ],
                "impact_estimate": "Better maintainability and performance"
            })
        
        return recommendations
    
    def sync_rules_across_network(self, rule_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Synchronize rules across the hAIveMind network"""
        if not self.redis_client:
            return {"success": False, "error": "Redis client not available"}
        
        try:
            sync_data = {
                "sync_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "source_machine": self.machine_id,
                "rule_ids": rule_ids,
                "operation": "sync_request"
            }
            
            # Export rules to sync
            if rule_ids:
                export_data = self.rule_service.db.export_rules("json", rule_ids)
            else:
                export_data = self.rule_service.db.export_rules("json")
            
            sync_data["rules_data"] = export_data
            
            # Broadcast sync request
            self.redis_client.publish('haivemind:rules:sync', json.dumps(sync_data))
            
            # Store sync operation as memory
            if self.memory_client:
                self.memory_client.store_memory(
                    content=f"Rules sync initiated: {len(rule_ids) if rule_ids else 'all'} rules",
                    category="rules",
                    metadata={
                        "sync_operation": sync_data,
                        "sharing_scope": "network-shared",
                        "importance": "medium",
                        "tags": ["sync", "rules", "network"]
                    }
                )
            
            return {
                "success": True,
                "sync_id": sync_data["sync_id"],
                "rules_count": len(rule_ids) if rule_ids else "all",
                "message": "Rules sync initiated successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to sync rules across network: {e}")
            return {"success": False, "error": str(e)}
    
    def get_network_rule_insights(self, days: int = 7) -> Dict[str, Any]:
        """Get insights about rule usage across the network"""
        if not self.memory_client:
            return {"error": "Memory client not available"}
        
        try:
            # Search for rule-related memories across the network
            search_results = self.memory_client.search_memories(
                query="rules governance network",
                filters={
                    "category": "rules",
                    "created_after": datetime.now() - timedelta(days=days)
                },
                limit=1000
            )
            
            # Analyze network patterns
            machine_usage = {}
            agent_usage = {}
            rule_distribution = {}
            operation_types = {}
            
            for memory in search_results:
                rule_data = memory.get('metadata', {}).get('rule_operation', {})
                machine_id = rule_data.get('machine_id', 'unknown')
                agent_id = rule_data.get('agent_id', 'unknown')
                rule_id = rule_data.get('rule_id')
                operation_type = rule_data.get('operation_type', 'unknown')
                
                # Count by machine
                machine_usage[machine_id] = machine_usage.get(machine_id, 0) + 1
                
                # Count by agent
                agent_usage[agent_id] = agent_usage.get(agent_id, 0) + 1
                
                # Count rule distribution
                if rule_id:
                    rule_distribution[rule_id] = rule_distribution.get(rule_id, 0) + 1
                
                # Count operation types
                operation_types[operation_type] = operation_types.get(operation_type, 0) + 1
            
            # Get top items
            top_machines = sorted(machine_usage.items(), key=lambda x: x[1], reverse=True)[:5]
            top_agents = sorted(agent_usage.items(), key=lambda x: x[1], reverse=True)[:5]
            top_rules = sorted(rule_distribution.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                "period_days": days,
                "total_operations": len(search_results),
                "machine_usage": dict(top_machines),
                "agent_usage": dict(top_agents),
                "top_rules": dict(top_rules),
                "operation_types": operation_types,
                "network_health": self._calculate_network_health(machine_usage, operation_types)
            }
            
        except Exception as e:
            logger.error(f"Failed to get network rule insights: {e}")
            return {"error": str(e)}
    
    def learn_from_rule_patterns(self, rule_id: str) -> Dict[str, Any]:
        """Learn from historical patterns to improve rule"""
        patterns = self.discover_rule_patterns()
        rule_patterns = [p for p in patterns if p.rule_id == rule_id]
        
        if not rule_patterns:
            return {"message": "No patterns found for this rule"}
        
        learning_insights = {
            "rule_id": rule_id,
            "patterns_found": len(rule_patterns),
            "insights": [],
            "recommendations": []
        }
        
        for pattern in rule_patterns:
            learning_insights["insights"].append({
                "type": pattern.insight_type,
                "description": pattern.description,
                "confidence": pattern.confidence,
                "data": pattern.data
            })
            
            learning_insights["recommendations"].extend(pattern.suggested_actions)
        
        # Remove duplicate recommendations
        learning_insights["recommendations"] = list(set(learning_insights["recommendations"]))
        
        # Store learning insights
        if self.memory_client:
            self.memory_client.store_memory(
                content=f"Learning insights for rule {rule_id}: {len(rule_patterns)} patterns analyzed",
                category="rules",
                metadata={
                    "learning_insights": learning_insights,
                    "sharing_scope": "network-shared",
                    "importance": "high",
                    "tags": ["learning", "insights", "patterns", rule_id[:8]]
                }
            )
        
        return learning_insights
    
    def _calculate_operation_importance(self, operation_type: str, outcome: Dict[str, Any]) -> str:
        """Calculate the importance level of a rule operation"""
        if operation_type in ['created', 'deleted']:
            return "high"
        elif operation_type in ['updated', 'activated', 'deactivated']:
            return "medium"
        elif not outcome.get('success', True):
            return "high"  # Failures are important
        else:
            return "low"
    
    def _broadcast_rule_operation(self, memory_entry: RuleMemoryEntry):
        """Broadcast rule operation to hAIveMind network"""
        try:
            message = {
                "type": "rule_operation",
                "data": asdict(memory_entry),
                "timestamp": datetime.now().isoformat()
            }
            self.redis_client.publish('haivemind:rules:operations', json.dumps(message, default=str))
        except Exception as e:
            logger.warning(f"Failed to broadcast rule operation: {e}")
    
    def _default_effectiveness_metric(self, rule_id: str) -> RuleEffectivenessMetric:
        """Return default effectiveness metric when analysis fails"""
        return RuleEffectivenessMetric(
            rule_id=rule_id,
            success_count=0,
            failure_count=0,
            avg_execution_time=0.0,
            effectiveness_score=0.0,
            last_evaluated=datetime.now(),
            recommendations=["Enable memory client for detailed analytics"]
        )
    
    def _generate_effectiveness_recommendations(self, score: float, avg_time: float, 
                                               total_evals: int) -> List[str]:
        """Generate recommendations based on effectiveness metrics"""
        recommendations = []
        
        if score < 0.5:
            recommendations.append("Review rule conditions for accuracy")
            recommendations.append("Add error handling for edge cases")
        elif score < 0.8:
            recommendations.append("Optimize rule conditions for better matching")
        
        if avg_time > 50:
            recommendations.append("Optimize complex conditions")
            recommendations.append("Consider caching for repeated evaluations")
        
        if total_evals < 5:
            recommendations.append("Increase rule usage or review relevance")
        
        return recommendations
    
    def _calculate_network_health(self, machine_usage: Dict[str, int], 
                                 operation_types: Dict[str, int]) -> Dict[str, Any]:
        """Calculate overall network health metrics"""
        total_machines = len(machine_usage)
        total_operations = sum(machine_usage.values())
        
        # Calculate distribution balance
        if total_operations > 0:
            avg_per_machine = total_operations / max(total_machines, 1)
            variance = sum((count - avg_per_machine) ** 2 for count in machine_usage.values()) / max(total_machines, 1)
            distribution_balance = max(0, 1 - (variance / (avg_per_machine ** 2))) if avg_per_machine > 0 else 0
        else:
            distribution_balance = 0
        
        # Calculate operation health
        error_operations = operation_types.get('error', 0) + operation_types.get('failed', 0)
        success_operations = total_operations - error_operations
        operation_health = success_operations / max(total_operations, 1) if total_operations > 0 else 1
        
        # Overall health score
        health_score = (distribution_balance + operation_health) / 2
        
        return {
            "health_score": round(health_score, 3),
            "distribution_balance": round(distribution_balance, 3),
            "operation_health": round(operation_health, 3),
            "active_machines": total_machines,
            "total_operations": total_operations,
            "status": "healthy" if health_score > 0.8 else "needs_attention" if health_score > 0.5 else "critical"
        }