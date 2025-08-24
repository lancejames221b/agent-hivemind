#!/usr/bin/env python3
"""
hAIveMind Rules Engine Performance Optimization System
Implements caching, indexing, and optimization strategies for rule evaluation

Author: Lance James, Unit 221B Inc
"""

import time
import hashlib
import json
import threading
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, asdict
from collections import defaultdict, OrderedDict
import logging
from datetime import datetime, timedelta

from .rules_engine import Rule, RuleCondition, RuleAction, RuleScope, RulePriority

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Rule evaluation performance metrics"""
    rule_id: str
    evaluation_count: int
    total_time_ms: float
    average_time_ms: float
    last_evaluated: datetime
    cache_hits: int = 0
    cache_misses: int = 0
    
    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0

@dataclass 
class CacheEntry:
    """Rule evaluation cache entry"""
    result: Dict[str, Any]
    created_at: datetime
    ttl_seconds: int
    access_count: int = 1
    
    @property
    def is_expired(self) -> bool:
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl_seconds)

class RuleIndex:
    """Optimized indexing for rule lookup and filtering"""
    
    def __init__(self):
        self.scope_index: Dict[RuleScope, Set[str]] = defaultdict(set)
        self.type_index: Dict[str, Set[str]] = defaultdict(set)
        self.priority_index: Dict[int, Set[str]] = defaultdict(set)
        self.field_index: Dict[str, Set[str]] = defaultdict(set)
        self.tag_index: Dict[str, Set[str]] = defaultdict(set)
        self.rules_by_id: Dict[str, Rule] = {}
        self._lock = threading.RLock()
    
    def add_rule(self, rule: Rule):
        """Add rule to all relevant indexes"""
        with self._lock:
            rule_id = rule.id
            self.rules_by_id[rule_id] = rule
            
            # Index by scope
            self.scope_index[rule.scope].add(rule_id)
            
            # Index by type
            self.type_index[rule.rule_type.value].add(rule_id)
            
            # Index by priority
            self.priority_index[rule.priority.value].add(rule_id)
            
            # Index by condition fields
            for condition in rule.conditions:
                self.field_index[condition.field].add(rule_id)
            
            # Index by tags
            for tag in rule.tags:
                self.tag_index[tag].add(rule_id)
    
    def remove_rule(self, rule_id: str):
        """Remove rule from all indexes"""
        with self._lock:
            rule = self.rules_by_id.get(rule_id)
            if not rule:
                return
                
            # Remove from all indexes
            self.scope_index[rule.scope].discard(rule_id)
            self.type_index[rule.rule_type.value].discard(rule_id)
            self.priority_index[rule.priority.value].discard(rule_id)
            
            for condition in rule.conditions:
                self.field_index[condition.field].discard(rule_id)
            
            for tag in rule.tags:
                self.tag_index[tag].discard(rule_id)
            
            del self.rules_by_id[rule_id]
    
    def find_rules(self, 
                   scope: Optional[RuleScope] = None,
                   rule_type: Optional[str] = None,
                   priority_min: Optional[int] = None,
                   priority_max: Optional[int] = None,
                   fields: Optional[List[str]] = None,
                   tags: Optional[List[str]] = None) -> List[Rule]:
        """Find rules matching criteria using indexes"""
        with self._lock:
            # Start with all rule IDs
            candidate_ids = set(self.rules_by_id.keys())
            
            # Apply filters using indexes
            if scope:
                candidate_ids &= self.scope_index[scope]
            
            if rule_type:
                candidate_ids &= self.type_index[rule_type]
            
            if priority_min is not None or priority_max is not None:
                priority_matches = set()
                for priority, rule_ids in self.priority_index.items():
                    if (priority_min is None or priority >= priority_min) and \
                       (priority_max is None or priority <= priority_max):
                        priority_matches.update(rule_ids)
                candidate_ids &= priority_matches
            
            if fields:
                # Rules must have conditions on at least one specified field
                field_matches = set()
                for field in fields:
                    field_matches.update(self.field_index[field])
                candidate_ids &= field_matches
            
            if tags:
                # Rules must have at least one specified tag
                tag_matches = set()
                for tag in tags:
                    tag_matches.update(self.tag_index[tag])
                candidate_ids &= tag_matches
            
            # Return actual rule objects
            return [self.rules_by_id[rule_id] for rule_id in candidate_ids]

class EvaluationCache:
    """LRU cache for rule evaluation results"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expired_removals': 0
        }
    
    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached evaluation result"""
        with self._lock:
            entry = self.cache.get(cache_key)
            if not entry:
                self._stats['misses'] += 1
                return None
            
            if entry.is_expired:
                del self.cache[cache_key]
                self._stats['expired_removals'] += 1
                self._stats['misses'] += 1
                return None
            
            # Move to end (most recently used)
            self.cache.move_to_end(cache_key)
            entry.access_count += 1
            self._stats['hits'] += 1
            
            return entry.result
    
    def put(self, cache_key: str, result: Dict[str, Any], ttl: Optional[int] = None):
        """Cache evaluation result"""
        with self._lock:
            # Remove if already exists
            if cache_key in self.cache:
                del self.cache[cache_key]
            
            # Add new entry
            entry = CacheEntry(
                result=result,
                created_at=datetime.now(),
                ttl_seconds=ttl or self.default_ttl
            )
            self.cache[cache_key] = entry
            
            # Enforce size limit
            while len(self.cache) > self.max_size:
                oldest_key, _ = self.cache.popitem(last=False)
                self._stats['evictions'] += 1
    
    def invalidate_by_pattern(self, pattern: str):
        """Invalidate cache entries matching pattern"""
        with self._lock:
            keys_to_remove = [key for key in self.cache.keys() if pattern in key]
            for key in keys_to_remove:
                del self.cache[key]
    
    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = self._stats['hits'] / total_requests if total_requests > 0 else 0.0
            
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hit_rate': hit_rate,
                **self._stats
            }

class ConditionOptimizer:
    """Optimizes rule condition evaluation order and logic"""
    
    @staticmethod
    def optimize_condition_order(conditions: List[RuleCondition]) -> List[RuleCondition]:
        """Reorder conditions for optimal evaluation performance"""
        if len(conditions) <= 1:
            return conditions
        
        # Sort by evaluation cost (lower cost first)
        def condition_cost(condition: RuleCondition) -> int:
            # Simple field comparisons are cheapest
            if condition.operator in ['eq', 'ne']:
                return 1
            # Contains and starts/ends with are medium cost
            elif condition.operator in ['contains', 'startswith', 'endswith']:
                return 2
            # List membership is medium-high cost
            elif condition.operator == 'in':
                return 3 + len(condition.value) if isinstance(condition.value, list) else 3
            # Regex is most expensive
            elif condition.operator == 'regex':
                return 10 + len(str(condition.value))
            else:
                return 5
        
        return sorted(conditions, key=condition_cost)
    
    @staticmethod
    def can_short_circuit(conditions: List[RuleCondition], context: Dict[str, Any]) -> Tuple[bool, int]:
        """Check if conditions can short-circuit evaluation"""
        for i, condition in enumerate(conditions):
            field_value = context.get(condition.field)
            
            # If field is missing and condition requires it, short-circuit
            if field_value is None and condition.operator not in ['exists', 'not_exists']:
                return True, i
            
            # Quick evaluation of simple conditions
            if condition.operator == 'eq' and field_value != condition.value:
                return True, i
            elif condition.operator == 'ne' and field_value == condition.value:
                return True, i
        
        return False, -1

class RulePerformanceManager:
    """Manages rule performance optimization and monitoring"""
    
    def __init__(self, redis_client=None, config: Dict[str, Any] = None):
        self.redis_client = redis_client
        self.config = config or {}
        
        # Performance components
        self.index = RuleIndex()
        self.cache = EvaluationCache(
            max_size=config.get('cache_size', 1000),
            default_ttl=config.get('cache_ttl', 300)
        )
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self._metrics_lock = threading.RLock()
        
        # Optimization settings
        self.enable_caching = config.get('enable_caching', True)
        self.enable_indexing = config.get('enable_indexing', True)
        self.enable_condition_optimization = config.get('enable_condition_optimization', True)
        
    def add_rule_to_index(self, rule: Rule):
        """Add rule to performance indexes"""
        if self.enable_indexing:
            self.index.add_rule(rule)
    
    def remove_rule_from_index(self, rule_id: str):
        """Remove rule from performance indexes"""
        if self.enable_indexing:
            self.index.remove_rule(rule_id)
    
    def find_applicable_rules(self, context: Dict[str, Any]) -> List[Rule]:
        """Find applicable rules using performance optimizations"""
        if not self.enable_indexing:
            return []  # Fallback to full scan
        
        # Extract search criteria from context
        scope = context.get('scope')
        rule_type = context.get('rule_type')
        fields = list(context.keys())
        
        return self.index.find_rules(
            scope=RuleScope(scope) if scope else None,
            rule_type=rule_type,
            fields=fields[:5]  # Limit field matching for performance
        )
    
    def evaluate_with_cache(self, rule: Rule, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate rule with caching optimization"""
        start_time = time.time()
        
        # Generate cache key
        cache_key = self._generate_cache_key(rule, context)
        
        # Try cache first
        cached_result = None
        if self.enable_caching:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                self._record_performance(rule.id, time.time() - start_time, cache_hit=True)
                return cached_result
        
        # Optimize conditions if enabled
        optimized_conditions = rule.conditions
        if self.enable_condition_optimization:
            optimized_conditions = ConditionOptimizer.optimize_condition_order(rule.conditions)
            
            # Check for short-circuit opportunities
            can_short_circuit, _ = ConditionOptimizer.can_short_circuit(optimized_conditions, context)
            if can_short_circuit:
                # Return early failure result
                result = {'applicable': False, 'short_circuited': True}
                if self.enable_caching:
                    self.cache.put(cache_key, result, ttl=60)  # Short TTL for negative results
                self._record_performance(rule.id, time.time() - start_time, cache_hit=False)
                return result
        
        # Evaluate rule (this would call the actual rule evaluation logic)
        result = self._evaluate_rule_impl(rule, context, optimized_conditions)
        
        # Cache result
        if self.enable_caching and result.get('cacheable', True):
            cache_ttl = self._calculate_cache_ttl(rule, result)
            self.cache.put(cache_key, result, ttl=cache_ttl)
        
        # Record performance metrics
        self._record_performance(rule.id, time.time() - start_time, cache_hit=False)
        
        return result
    
    def _generate_cache_key(self, rule: Rule, context: Dict[str, Any]) -> str:
        """Generate cache key for rule evaluation"""
        # Include rule ID and version
        key_data = {
            'rule_id': rule.id,
            'rule_version': rule.version,
            'context': {k: v for k, v in context.items() if k in ['agent_id', 'machine_id', 'project_id']}
        }
        
        # Hash for deterministic key
        key_string = json.dumps(key_data, sort_keys=True)
        return f"rule_eval:{hashlib.md5(key_string.encode()).hexdigest()}"
    
    def _calculate_cache_ttl(self, rule: Rule, result: Dict[str, Any]) -> int:
        """Calculate appropriate cache TTL based on rule characteristics"""
        base_ttl = self.cache.default_ttl
        
        # Longer TTL for stable rule types
        if rule.rule_type.value in ['authorship', 'security']:
            return base_ttl * 2
        
        # Shorter TTL for dynamic results
        if result.get('dynamic', False):
            return base_ttl // 2
        
        # Longer TTL for high-priority rules
        if rule.priority.value >= 750:
            return base_ttl * 1.5
        
        return base_ttl
    
    def _evaluate_rule_impl(self, rule: Rule, context: Dict[str, Any], conditions: List[RuleCondition]) -> Dict[str, Any]:
        """Placeholder for actual rule evaluation logic"""
        # This would contain the actual evaluation logic
        # For now, return a simple result
        return {
            'applicable': True,
            'rule_id': rule.id,
            'evaluated_conditions': len(conditions),
            'cacheable': True
        }
    
    def _record_performance(self, rule_id: str, execution_time: float, cache_hit: bool = False):
        """Record performance metrics for rule"""
        with self._metrics_lock:
            if rule_id not in self.metrics:
                self.metrics[rule_id] = PerformanceMetrics(
                    rule_id=rule_id,
                    evaluation_count=0,
                    total_time_ms=0,
                    average_time_ms=0,
                    last_evaluated=datetime.now()
                )
            
            metrics = self.metrics[rule_id]
            metrics.evaluation_count += 1
            metrics.total_time_ms += execution_time * 1000
            metrics.average_time_ms = metrics.total_time_ms / metrics.evaluation_count
            metrics.last_evaluated = datetime.now()
            
            if cache_hit:
                metrics.cache_hits += 1
            else:
                metrics.cache_misses += 1
    
    def get_performance_report(self, top_n: int = 10) -> Dict[str, Any]:
        """Generate performance report for rules"""
        with self._metrics_lock:
            # Sort by average execution time
            sorted_metrics = sorted(
                self.metrics.values(),
                key=lambda m: m.average_time_ms,
                reverse=True
            )
            
            # Cache statistics
            cache_stats = self.cache.get_stats()
            
            # Top slow rules
            slow_rules = sorted_metrics[:top_n]
            
            # Most frequently evaluated
            frequent_rules = sorted(
                self.metrics.values(),
                key=lambda m: m.evaluation_count,
                reverse=True
            )[:top_n]
            
            # Overall statistics
            total_evaluations = sum(m.evaluation_count for m in self.metrics.values())
            total_time = sum(m.total_time_ms for m in self.metrics.values())
            avg_time = total_time / total_evaluations if total_evaluations > 0 else 0
            
            return {
                'summary': {
                    'total_rules_evaluated': len(self.metrics),
                    'total_evaluations': total_evaluations,
                    'total_time_ms': total_time,
                    'average_time_ms': avg_time
                },
                'cache_stats': cache_stats,
                'slowest_rules': [asdict(m) for m in slow_rules],
                'most_frequent_rules': [asdict(m) for m in frequent_rules]
            }
    
    def optimize_rule_set(self, rules: List[Rule]) -> Dict[str, Any]:
        """Analyze and suggest optimizations for rule set"""
        suggestions = []
        
        # Analyze rule complexity
        complex_rules = []
        for rule in rules:
            complexity_score = self._calculate_rule_complexity(rule)
            if complexity_score > 10:
                complex_rules.append((rule, complexity_score))
        
        if complex_rules:
            suggestions.append({
                'type': 'complexity',
                'message': f'{len(complex_rules)} rules have high complexity',
                'details': [{'rule_id': r.id, 'score': score} for r, score in complex_rules[:5]]
            })
        
        # Check for cache miss rates
        high_miss_rules = []
        with self._metrics_lock:
            for metrics in self.metrics.values():
                if metrics.cache_hit_rate < 0.5 and metrics.evaluation_count > 10:
                    high_miss_rules.append(metrics)
        
        if high_miss_rules:
            suggestions.append({
                'type': 'cache_efficiency',
                'message': f'{len(high_miss_rules)} rules have low cache hit rates',
                'details': [{'rule_id': m.rule_id, 'hit_rate': m.cache_hit_rate} 
                          for m in high_miss_rules[:5]]
            })
        
        # Index utilization
        index_stats = {
            'scope_distribution': {scope.value: len(rule_ids) 
                                 for scope, rule_ids in self.index.scope_index.items()},
            'type_distribution': {rule_type: len(rule_ids)
                                for rule_type, rule_ids in self.index.type_index.items()}
        }
        
        return {
            'suggestions': suggestions,
            'index_stats': index_stats,
            'total_analyzed': len(rules)
        }
    
    def _calculate_rule_complexity(self, rule: Rule) -> int:
        """Calculate complexity score for a rule"""
        score = 0
        
        # Condition complexity
        for condition in rule.conditions:
            if condition.operator == 'regex':
                score += 5 + len(str(condition.value)) // 10
            elif condition.operator == 'in':
                score += 2 + (len(condition.value) if isinstance(condition.value, list) else 0)
            else:
                score += 1
        
        # Action complexity
        for action in rule.actions:
            if action.action_type in ['transform', 'invoke']:
                score += 3
            elif action.action_type in ['merge', 'validate']:
                score += 2
            else:
                score += 1
        
        return score