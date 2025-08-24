#!/usr/bin/env python3
"""
hAIveMind Rules Engine Integration
Connects rules engine with hAIveMind memory system for awareness and learning

Author: Lance James, Unit 221B Inc
"""

import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
import threading
from dataclasses import dataclass, asdict

from .rules_engine import RulesEngine, Rule, RuleType, RuleScope
from .rule_performance import RulePerformanceManager, PerformanceMetrics

logger = logging.getLogger(__name__)

@dataclass
class RuleEvent:
    """Event for rule-related activities"""
    event_id: str
    event_type: str  # evaluation, conflict, optimization, etc.
    rule_ids: List[str]
    agent_id: str
    machine_id: str
    context: Dict[str, Any]
    result: Dict[str, Any]
    timestamp: datetime
    metadata: Dict[str, Any] = None

@dataclass
class RuleLearning:
    """Learning data from rule evaluations"""
    pattern_id: str
    pattern_type: str  # effectiveness, conflict, optimization
    rule_ids: List[str]
    context_patterns: Dict[str, Any]
    success_metrics: Dict[str, float]
    failure_modes: List[str]
    recommendations: List[str]
    confidence: float
    learned_at: datetime

class hAIveMindRulesIntegration:
    """Integrates Rules Engine with hAIveMind memory and awareness system"""
    
    def __init__(self, rules_engine: RulesEngine, memory_storage, redis_client=None):
        self.rules_engine = rules_engine
        self.memory_storage = memory_storage
        self.redis_client = redis_client
        
        # Learning and awareness components
        self.event_buffer: List[RuleEvent] = []
        self.learning_patterns: Dict[str, RuleLearning] = {}
        self.buffer_lock = threading.RLock()
        
        # Performance tracking integration
        self.performance_manager = RulePerformanceManager(
            redis_client=redis_client,
            config={'enable_caching': True, 'enable_indexing': True}
        )
        
        # hAIveMind channels
        self.broadcast_channel = "haivemind:rules:broadcast"
        self.learning_channel = "haivemind:rules:learning"
        
    def evaluate_with_awareness(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate rules with hAIveMind awareness and learning"""
        evaluation_start = time.time()
        
        # Standard rule evaluation
        evaluation_result = self.rules_engine.evaluate_rules(context)
        
        # Create event for awareness
        event = RuleEvent(
            event_id=str(uuid.uuid4()),
            event_type="evaluation",
            rule_ids=evaluation_result.get('applied_rules', []),
            agent_id=context.get('agent_id', 'unknown'),
            machine_id=context.get('machine_id', 'unknown'),
            context=context,
            result=evaluation_result,
            timestamp=datetime.now(),
            metadata={
                'evaluation_time_ms': evaluation_result.get('evaluation_time_ms', 0),
                'context_hash': evaluation_result.get('context_hash', '')
            }
        )
        
        # Record event for learning
        self._record_event(event)
        
        # Store evaluation as hAIveMind memory
        self._store_evaluation_memory(event)
        
        # Broadcast to other agents if significant
        if self._is_significant_evaluation(event):
            self._broadcast_evaluation(event)
        
        # Update performance tracking
        for rule_id in event.rule_ids:
            self.performance_manager._record_performance(
                rule_id, 
                evaluation_result.get('evaluation_time_ms', 0) / 1000,
                cache_hit=False
            )
        
        return evaluation_result
    
    def learn_from_patterns(self) -> List[RuleLearning]:
        """Analyze patterns and generate learning insights"""
        with self.buffer_lock:
            if len(self.event_buffer) < 10:  # Need minimum events for pattern learning
                return []
        
        new_learnings = []
        
        # Analyze effectiveness patterns
        effectiveness_learning = self._analyze_effectiveness_patterns()
        if effectiveness_learning:
            new_learnings.append(effectiveness_learning)
        
        # Analyze conflict patterns
        conflict_learning = self._analyze_conflict_patterns()
        if conflict_learning:
            new_learnings.append(conflict_learning)
        
        # Analyze performance patterns
        performance_learning = self._analyze_performance_patterns()
        if performance_learning:
            new_learnings.append(performance_learning)
        
        # Store learnings
        for learning in new_learnings:
            self.learning_patterns[learning.pattern_id] = learning
            self._store_learning_memory(learning)
            self._broadcast_learning(learning)
        
        return new_learnings
    
    def suggest_rule_improvements(self, rule_id: str) -> List[Dict[str, Any]]:
        """Suggest improvements for specific rule based on learned patterns"""
        suggestions = []
        
        # Get rule performance metrics
        performance_report = self.performance_manager.get_performance_report()
        rule_metrics = None
        
        for metrics_dict in performance_report.get('slowest_rules', []):
            if metrics_dict['rule_id'] == rule_id:
                rule_metrics = metrics_dict
                break
        
        if rule_metrics:
            # Performance-based suggestions
            if rule_metrics['average_time_ms'] > 50:
                suggestions.append({
                    'type': 'performance',
                    'priority': 'high',
                    'message': f"Rule evaluation is slow ({rule_metrics['average_time_ms']:.1f}ms average)",
                    'recommendations': [
                        'Simplify complex conditions',
                        'Consider condition reordering',
                        'Add more specific conditions to reduce applicability'
                    ]
                })
            
            if rule_metrics.get('cache_hit_rate', 0) < 0.3:
                suggestions.append({
                    'type': 'caching',
                    'priority': 'medium',
                    'message': f"Low cache hit rate ({rule_metrics.get('cache_hit_rate', 0):.1%})",
                    'recommendations': [
                        'Make rule conditions more deterministic',
                        'Increase cache TTL for stable rules',
                        'Consider context-specific variations'
                    ]
                })
        
        # Learning-based suggestions
        relevant_learnings = [l for l in self.learning_patterns.values() 
                            if rule_id in l.rule_ids]
        
        for learning in relevant_learnings:
            if learning.pattern_type == 'effectiveness' and learning.confidence > 0.7:
                for failure_mode in learning.failure_modes:
                    suggestions.append({
                        'type': 'effectiveness',
                        'priority': 'high',
                        'message': f"Detected failure pattern: {failure_mode}",
                        'recommendations': learning.recommendations
                    })
        
        return suggestions
    
    def get_network_rule_insights(self) -> Dict[str, Any]:
        """Get insights from across the hAIveMind network"""
        insights = {
            'local_rules': len(self.rules_engine.db.get_all_rule_ids() if hasattr(self.rules_engine.db, 'get_all_rule_ids') else []),
            'local_evaluations': len(self.event_buffer),
            'learning_patterns': len(self.learning_patterns),
            'network_insights': []
        }
        
        # Query network for rule insights via Redis
        if self.redis_client:
            try:
                # Get network rule statistics
                network_stats = self._query_network_stats()
                insights['network_insights'] = network_stats
                
                # Get shared learnings
                shared_learnings = self._get_shared_learnings()
                insights['shared_learnings'] = len(shared_learnings)
                
            except Exception as e:
                logger.warning(f"Failed to get network insights: {e}")
        
        return insights
    
    def sync_rules_across_network(self, rule_ids: Optional[List[str]] = None):
        """Synchronize rules across hAIveMind network"""
        if not self.redis_client:
            logger.warning("Redis not available for network sync")
            return
        
        sync_data = {
            'sync_id': str(uuid.uuid4()),
            'source_machine': self.memory_storage.machine_id if hasattr(self.memory_storage, 'machine_id') else 'unknown',
            'timestamp': datetime.now().isoformat(),
            'rule_ids': rule_ids or [],
            'sync_type': 'partial' if rule_ids else 'full'
        }
        
        # Publish sync request
        try:
            self.redis_client.publish(
                "haivemind:rules:sync_request",
                json.dumps(sync_data)
            )
            logger.info(f"Published rule sync request: {sync_data['sync_id']}")
        except Exception as e:
            logger.error(f"Failed to publish sync request: {e}")
    
    def _record_event(self, event: RuleEvent):
        """Record rule event for pattern analysis"""
        with self.buffer_lock:
            self.event_buffer.append(event)
            
            # Maintain buffer size
            if len(self.event_buffer) > 1000:
                self.event_buffer = self.event_buffer[-800:]  # Keep most recent 800
    
    def _store_evaluation_memory(self, event: RuleEvent):
        """Store rule evaluation as hAIveMind memory"""
        try:
            memory_content = {
                'type': 'rule_evaluation',
                'event_id': event.event_id,
                'applied_rules': event.rule_ids,
                'context_summary': self._summarize_context(event.context),
                'result_summary': self._summarize_result(event.result),
                'performance': event.metadata
            }
            
            # Store via memory storage system
            if hasattr(self.memory_storage, 'store_memory'):
                self.memory_storage.store_memory(
                    content=json.dumps(memory_content),
                    category='rules',
                    metadata={
                        'event_type': event.event_type,
                        'agent_id': event.agent_id,
                        'machine_id': event.machine_id,
                        'rule_count': len(event.rule_ids)
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to store evaluation memory: {e}")
    
    def _store_learning_memory(self, learning: RuleLearning):
        """Store rule learning as hAIveMind memory"""
        try:
            memory_content = {
                'type': 'rule_learning',
                'pattern_id': learning.pattern_id,
                'pattern_type': learning.pattern_type,
                'affected_rules': learning.rule_ids,
                'insights': learning.recommendations,
                'confidence': learning.confidence,
                'context_patterns': learning.context_patterns
            }
            
            if hasattr(self.memory_storage, 'store_memory'):
                self.memory_storage.store_memory(
                    content=json.dumps(memory_content),
                    category='rules',
                    metadata={
                        'learning_type': learning.pattern_type,
                        'confidence': learning.confidence,
                        'rule_count': len(learning.rule_ids)
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to store learning memory: {e}")
    
    def _broadcast_evaluation(self, event: RuleEvent):
        """Broadcast significant rule evaluation to network"""
        if not self.redis_client:
            return
        
        broadcast_data = {
            'type': 'rule_evaluation',
            'source_machine': event.machine_id,
            'source_agent': event.agent_id,
            'rule_ids': event.rule_ids,
            'context_type': event.context.get('task_type', 'unknown'),
            'effectiveness': self._calculate_effectiveness(event),
            'timestamp': event.timestamp.isoformat()
        }
        
        try:
            self.redis_client.publish(self.broadcast_channel, json.dumps(broadcast_data))
        except Exception as e:
            logger.warning(f"Failed to broadcast evaluation: {e}")
    
    def _broadcast_learning(self, learning: RuleLearning):
        """Broadcast learning insight to network"""
        if not self.redis_client:
            return
        
        broadcast_data = {
            'type': 'rule_learning',
            'pattern_id': learning.pattern_id,
            'pattern_type': learning.pattern_type,
            'confidence': learning.confidence,
            'recommendations': learning.recommendations[:3],  # Limit size
            'timestamp': learning.learned_at.isoformat()
        }
        
        try:
            self.redis_client.publish(self.learning_channel, json.dumps(broadcast_data))
        except Exception as e:
            logger.warning(f"Failed to broadcast learning: {e}")
    
    def _is_significant_evaluation(self, event: RuleEvent) -> bool:
        """Determine if evaluation is significant enough to broadcast"""
        # Significant if:
        # - Many rules applied
        # - Slow evaluation
        # - Conflicts detected
        # - New context pattern
        
        if len(event.rule_ids) > 5:
            return True
        
        if event.metadata.get('evaluation_time_ms', 0) > 100:
            return True
        
        if 'conflict' in event.result:
            return True
        
        return False
    
    def _analyze_effectiveness_patterns(self) -> Optional[RuleLearning]:
        """Analyze rule effectiveness patterns"""
        with self.buffer_lock:
            recent_events = [e for e in self.event_buffer 
                           if e.timestamp > datetime.now() - timedelta(hours=24)]
        
        if len(recent_events) < 20:
            return None
        
        # Group by rule combinations
        rule_combinations = {}
        for event in recent_events:
            key = tuple(sorted(event.rule_ids))
            if key not in rule_combinations:
                rule_combinations[key] = []
            rule_combinations[key].append(event)
        
        # Find patterns with sufficient data
        significant_combinations = {k: v for k, v in rule_combinations.items() 
                                  if len(v) >= 5}
        
        if not significant_combinations:
            return None
        
        # Analyze most common combination
        most_common = max(significant_combinations.items(), key=lambda x: len(x[1]))
        rule_ids, events = most_common
        
        # Calculate effectiveness metrics
        avg_time = sum(e.metadata.get('evaluation_time_ms', 0) for e in events) / len(events)
        
        recommendations = []
        failure_modes = []
        
        if avg_time > 50:
            recommendations.append("Optimize slow rule combination")
            failure_modes.append("slow_evaluation")
        
        context_patterns = self._extract_context_patterns([e.context for e in events])
        
        return RuleLearning(
            pattern_id=f"effectiveness_{uuid.uuid4().hex[:8]}",
            pattern_type="effectiveness",
            rule_ids=list(rule_ids),
            context_patterns=context_patterns,
            success_metrics={'average_time_ms': avg_time, 'frequency': len(events)},
            failure_modes=failure_modes,
            recommendations=recommendations,
            confidence=min(0.9, len(events) / 50),  # Higher confidence with more data
            learned_at=datetime.now()
        )
    
    def _analyze_conflict_patterns(self) -> Optional[RuleLearning]:
        """Analyze rule conflict patterns"""
        # Placeholder for conflict analysis
        # Would analyze events where conflicts occurred
        return None
    
    def _analyze_performance_patterns(self) -> Optional[RuleLearning]:
        """Analyze performance patterns from evaluations"""
        performance_report = self.performance_manager.get_performance_report()
        
        if not performance_report.get('slowest_rules'):
            return None
        
        slow_rules = performance_report['slowest_rules'][:5]
        slow_rule_ids = [r['rule_id'] for r in slow_rules]
        
        recommendations = [
            "Consider caching for frequently evaluated rules",
            "Optimize condition evaluation order",
            "Simplify complex rule conditions"
        ]
        
        return RuleLearning(
            pattern_id=f"performance_{uuid.uuid4().hex[:8]}",
            pattern_type="performance",
            rule_ids=slow_rule_ids,
            context_patterns={'evaluation_frequency': 'high'},
            success_metrics={'average_improvement_potential': 30.0},
            failure_modes=['slow_evaluation', 'cache_miss'],
            recommendations=recommendations,
            confidence=0.8,
            learned_at=datetime.now()
        )
    
    def _summarize_context(self, context: Dict[str, Any]) -> str:
        """Create summary of evaluation context"""
        key_fields = ['agent_id', 'machine_id', 'project_id', 'task_type']
        summary_parts = []
        
        for field in key_fields:
            if field in context:
                summary_parts.append(f"{field}={context[field]}")
        
        return ", ".join(summary_parts)
    
    def _summarize_result(self, result: Dict[str, Any]) -> str:
        """Create summary of evaluation result"""
        applied_count = len(result.get('applied_rules', []))
        eval_time = result.get('evaluation_time_ms', 0)
        
        return f"Applied {applied_count} rules in {eval_time:.1f}ms"
    
    def _calculate_effectiveness(self, event: RuleEvent) -> float:
        """Calculate effectiveness score for evaluation"""
        base_score = 0.5
        
        # Fast evaluations are more effective
        eval_time = event.metadata.get('evaluation_time_ms', 0)
        if eval_time < 10:
            base_score += 0.3
        elif eval_time > 100:
            base_score -= 0.2
        
        # More rules applied suggests good matching
        rule_count = len(event.rule_ids)
        if rule_count > 3:
            base_score += 0.2
        
        return max(0.0, min(1.0, base_score))
    
    def _extract_context_patterns(self, contexts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract common patterns from contexts"""
        patterns = {}
        
        # Find most common values for each field
        field_values = {}
        for context in contexts:
            for field, value in context.items():
                if field not in field_values:
                    field_values[field] = {}
                field_values[field][value] = field_values[field].get(value, 0) + 1
        
        # Extract most common values
        for field, values in field_values.items():
            if values:
                most_common = max(values.items(), key=lambda x: x[1])
                if most_common[1] > len(contexts) * 0.5:  # Appears in >50% of contexts
                    patterns[field] = most_common[0]
        
        return patterns
    
    def _query_network_stats(self) -> List[Dict[str, Any]]:
        """Query network for rule statistics"""
        # Placeholder - would query other machines via Redis
        return []
    
    def _get_shared_learnings(self) -> List[Dict[str, Any]]:
        """Get shared learning patterns from network"""
        # Placeholder - would retrieve from Redis or memory storage
        return []