#!/usr/bin/env python3
"""
Rule Performance Analyzer - Analytics and optimization for hAIveMind Rules
Provides performance monitoring, usage analytics, and optimization suggestions

Author: Lance James, Unit 221B Inc
"""

import json
import sqlite3
import time
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict, Counter

from .rules_engine import Rule, RuleType, RuleScope, RulePriority, RuleStatus

@dataclass
class RulePerformanceMetrics:
    """Performance metrics for a rule"""
    rule_id: str
    rule_name: str
    total_evaluations: int
    successful_evaluations: int
    failed_evaluations: int
    average_execution_time_ms: float
    median_execution_time_ms: float
    min_execution_time_ms: float
    max_execution_time_ms: float
    last_evaluation: Optional[datetime]
    success_rate: float
    usage_frequency: float  # evaluations per day
    performance_score: float  # 0-100 score based on speed and reliability

@dataclass
class RuleUsagePattern:
    """Usage pattern analysis for rules"""
    rule_id: str
    peak_usage_hours: List[int]  # Hours of day with highest usage
    usage_by_agent: Dict[str, int]
    usage_by_machine: Dict[str, int]
    usage_by_context: Dict[str, int]
    seasonal_patterns: Dict[str, float]  # Weekly/monthly patterns
    correlation_with_other_rules: Dict[str, float]

@dataclass
class OptimizationSuggestion:
    """Rule optimization suggestion"""
    rule_id: str
    suggestion_type: str
    priority: str  # high, medium, low
    description: str
    expected_improvement: str
    implementation_effort: str  # low, medium, high
    metadata: Dict[str, Any]

class RulePerformanceAnalyzer:
    """Comprehensive rule performance analysis and optimization"""
    
    def __init__(self, rules_db):
        self.rules_db = rules_db
        self.performance_cache = {}
        self.cache_ttl = 300  # 5 minutes cache TTL
        self.last_cache_update = {}
    
    def get_rule_analytics(self, rule_id: str, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive analytics for a specific rule"""
        try:
            with sqlite3.connect(self.rules_db.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Get rule evaluations
                cursor = conn.execute("""
                    SELECT * FROM rule_evaluations 
                    WHERE rule_id = ? AND created_at > datetime('now', '-{} days')
                    ORDER BY created_at DESC
                """.format(days), (rule_id,))
                
                evaluations = cursor.fetchall()
                
                if not evaluations:
                    return {
                        "rule_id": rule_id,
                        "total_evaluations": 0,
                        "performance_metrics": None,
                        "usage_patterns": None,
                        "optimization_suggestions": []
                    }
                
                # Calculate performance metrics
                metrics = self._calculate_performance_metrics(rule_id, evaluations)
                
                # Analyze usage patterns
                patterns = self._analyze_usage_patterns(rule_id, evaluations)
                
                # Generate optimization suggestions
                suggestions = self._generate_optimization_suggestions(rule_id, metrics, patterns)
                
                return {
                    "rule_id": rule_id,
                    "total_evaluations": len(evaluations),
                    "performance_metrics": metrics.__dict__ if metrics else None,
                    "usage_patterns": patterns.__dict__ if patterns else None,
                    "optimization_suggestions": [s.__dict__ for s in suggestions],
                    "analysis_period_days": days,
                    "generated_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            print(f"Error getting rule analytics for {rule_id}: {e}")
            return {
                "rule_id": rule_id,
                "error": str(e),
                "total_evaluations": 0
            }
    
    def get_overall_performance(self, days: int = 30) -> Dict[str, Any]:
        """Get overall performance metrics across all rules"""
        try:
            with sqlite3.connect(self.rules_db.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Get all evaluations in the period
                cursor = conn.execute("""
                    SELECT re.*, r.name, r.rule_type, r.scope, r.priority 
                    FROM rule_evaluations re
                    JOIN rules r ON re.rule_id = r.id
                    WHERE re.created_at > datetime('now', '-{} days')
                """.format(days))
                
                evaluations = cursor.fetchall()
                
                if not evaluations:
                    return {"total_evaluations": 0, "message": "No evaluation data available"}
                
                # Calculate overall metrics
                total_evaluations = len(evaluations)
                execution_times = [eval['execution_time_ms'] for eval in evaluations]
                
                # Group by rule type
                by_rule_type = defaultdict(list)
                by_scope = defaultdict(list)
                by_priority = defaultdict(list)
                
                for eval in evaluations:
                    by_rule_type[eval['rule_type']].append(eval['execution_time_ms'])
                    by_scope[eval['scope']].append(eval['execution_time_ms'])
                    by_priority[eval['priority']].append(eval['execution_time_ms'])
                
                return {
                    "total_evaluations": total_evaluations,
                    "overall_performance": {
                        "average_execution_time_ms": statistics.mean(execution_times),
                        "median_execution_time_ms": statistics.median(execution_times),
                        "min_execution_time_ms": min(execution_times),
                        "max_execution_time_ms": max(execution_times),
                        "std_deviation_ms": statistics.stdev(execution_times) if len(execution_times) > 1 else 0
                    },
                    "performance_by_rule_type": {
                        rule_type: {
                            "count": len(times),
                            "average_time_ms": statistics.mean(times),
                            "median_time_ms": statistics.median(times)
                        }
                        for rule_type, times in by_rule_type.items()
                    },
                    "performance_by_scope": {
                        scope: {
                            "count": len(times),
                            "average_time_ms": statistics.mean(times),
                            "median_time_ms": statistics.median(times)
                        }
                        for scope, times in by_scope.items()
                    },
                    "performance_by_priority": {
                        str(priority): {
                            "count": len(times),
                            "average_time_ms": statistics.mean(times),
                            "median_time_ms": statistics.median(times)
                        }
                        for priority, times in by_priority.items()
                    },
                    "analysis_period_days": days,
                    "generated_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            print(f"Error getting overall performance: {e}")
            return {"error": str(e)}
    
    def get_usage_patterns(self, days: int = 30) -> Dict[str, Any]:
        """Get usage patterns across all rules"""
        try:
            with sqlite3.connect(self.rules_db.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                cursor = conn.execute("""
                    SELECT re.*, r.name, r.rule_type 
                    FROM rule_evaluations re
                    JOIN rules r ON re.rule_id = r.id
                    WHERE re.created_at > datetime('now', '-{} days')
                """.format(days))
                
                evaluations = cursor.fetchall()
                
                if not evaluations:
                    return {"message": "No usage data available"}
                
                # Analyze patterns
                hourly_usage = defaultdict(int)
                daily_usage = defaultdict(int)
                agent_usage = defaultdict(int)
                machine_usage = defaultdict(int)
                rule_type_usage = defaultdict(int)
                
                for eval in evaluations:
                    # Parse timestamp
                    eval_time = datetime.fromisoformat(eval['created_at'])
                    
                    hourly_usage[eval_time.hour] += 1
                    daily_usage[eval_time.strftime('%Y-%m-%d')] += 1
                    agent_usage[eval['agent_id']] += 1
                    machine_usage[eval['machine_id']] += 1
                    rule_type_usage[eval['rule_type']] += 1
                
                # Find peak hours
                peak_hours = sorted(hourly_usage.items(), key=lambda x: x[1], reverse=True)[:3]
                
                # Find most active agents/machines
                top_agents = sorted(agent_usage.items(), key=lambda x: x[1], reverse=True)[:5]
                top_machines = sorted(machine_usage.items(), key=lambda x: x[1], reverse=True)[:5]
                
                return {
                    "total_evaluations": len(evaluations),
                    "peak_usage_hours": [{"hour": h, "count": c} for h, c in peak_hours],
                    "daily_usage_trend": dict(daily_usage),
                    "hourly_distribution": dict(hourly_usage),
                    "top_agents": [{"agent_id": a, "evaluations": c} for a, c in top_agents],
                    "top_machines": [{"machine_id": m, "evaluations": c} for m, c in top_machines],
                    "rule_type_distribution": dict(rule_type_usage),
                    "analysis_period_days": days,
                    "generated_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            print(f"Error getting usage patterns: {e}")
            return {"error": str(e)}
    
    def get_optimization_recommendations(self, limit: int = 10) -> List[OptimizationSuggestion]:
        """Get top optimization recommendations across all rules"""
        try:
            recommendations = []
            
            # Get all rules with performance data
            with sqlite3.connect(self.rules_db.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                cursor = conn.execute("""
                    SELECT r.id, r.name, r.rule_type, r.scope, r.priority,
                           COUNT(re.id) as evaluation_count,
                           AVG(re.execution_time_ms) as avg_time,
                           MAX(re.execution_time_ms) as max_time
                    FROM rules r
                    LEFT JOIN rule_evaluations re ON r.id = re.rule_id
                    WHERE re.created_at > datetime('now', '-30 days')
                    GROUP BY r.id, r.name, r.rule_type, r.scope, r.priority
                    HAVING evaluation_count > 0
                    ORDER BY avg_time DESC
                """)
                
                rules_with_performance = cursor.fetchall()
                
                for rule_data in rules_with_performance:
                    rule_suggestions = self._generate_rule_optimization_suggestions(rule_data)
                    recommendations.extend(rule_suggestions)
                
                # Sort by priority and limit
                recommendations.sort(key=lambda x: self._get_priority_score(x.priority), reverse=True)
                return recommendations[:limit]
                
        except Exception as e:
            print(f"Error getting optimization recommendations: {e}")
            return []
    
    def _calculate_performance_metrics(self, rule_id: str, evaluations: List) -> Optional[RulePerformanceMetrics]:
        """Calculate performance metrics from evaluation data"""
        try:
            if not evaluations:
                return None
            
            # Get rule name
            rule_name = "Unknown"
            try:
                rule = self.rules_db.get_rule(rule_id)
                if rule:
                    rule_name = rule.name
            except:
                pass
            
            # Extract execution times and results
            execution_times = []
            successful_evals = 0
            failed_evals = 0
            
            for eval in evaluations:
                execution_times.append(eval['execution_time_ms'])
                
                # Determine success/failure based on result
                try:
                    result = json.loads(eval['result'])
                    if result.get('success', True):  # Default to success if not specified
                        successful_evals += 1
                    else:
                        failed_evals += 1
                except:
                    successful_evals += 1  # Assume success if can't parse result
            
            total_evals = len(evaluations)
            success_rate = (successful_evals / total_evals) * 100 if total_evals > 0 else 0
            
            # Calculate usage frequency (evaluations per day)
            days_span = 30  # Default analysis period
            usage_frequency = total_evals / days_span
            
            # Calculate performance score (0-100)
            avg_time = statistics.mean(execution_times)
            performance_score = self._calculate_performance_score(avg_time, success_rate, usage_frequency)
            
            # Get last evaluation time
            last_eval = None
            if evaluations:
                try:
                    last_eval = datetime.fromisoformat(evaluations[0]['created_at'])
                except:
                    pass
            
            return RulePerformanceMetrics(
                rule_id=rule_id,
                rule_name=rule_name,
                total_evaluations=total_evals,
                successful_evaluations=successful_evals,
                failed_evaluations=failed_evals,
                average_execution_time_ms=avg_time,
                median_execution_time_ms=statistics.median(execution_times),
                min_execution_time_ms=min(execution_times),
                max_execution_time_ms=max(execution_times),
                last_evaluation=last_eval,
                success_rate=success_rate,
                usage_frequency=usage_frequency,
                performance_score=performance_score
            )
            
        except Exception as e:
            print(f"Error calculating performance metrics for {rule_id}: {e}")
            return None
    
    def _analyze_usage_patterns(self, rule_id: str, evaluations: List) -> Optional[RuleUsagePattern]:
        """Analyze usage patterns from evaluation data"""
        try:
            if not evaluations:
                return None
            
            hourly_usage = defaultdict(int)
            agent_usage = defaultdict(int)
            machine_usage = defaultdict(int)
            context_usage = defaultdict(int)
            
            for eval in evaluations:
                # Parse timestamp for hourly patterns
                try:
                    eval_time = datetime.fromisoformat(eval['created_at'])
                    hourly_usage[eval_time.hour] += 1
                except:
                    pass
                
                # Count usage by agent and machine
                agent_usage[eval['agent_id']] += 1
                machine_usage[eval['machine_id']] += 1
                
                # Analyze context patterns
                try:
                    context = json.loads(eval['evaluation_context'])
                    for key, value in context.items():
                        context_key = f"{key}:{value}"
                        context_usage[context_key] += 1
                except:
                    pass
            
            # Find peak usage hours
            peak_hours = sorted(hourly_usage.keys(), key=lambda h: hourly_usage[h], reverse=True)[:3]
            
            return RuleUsagePattern(
                rule_id=rule_id,
                peak_usage_hours=peak_hours,
                usage_by_agent=dict(agent_usage),
                usage_by_machine=dict(machine_usage),
                usage_by_context=dict(context_usage),
                seasonal_patterns={},  # Would require more complex analysis
                correlation_with_other_rules={}  # Would require cross-rule analysis
            )
            
        except Exception as e:
            print(f"Error analyzing usage patterns for {rule_id}: {e}")
            return None
    
    def _generate_optimization_suggestions(self, rule_id: str, metrics: RulePerformanceMetrics, patterns: RuleUsagePattern) -> List[OptimizationSuggestion]:
        """Generate optimization suggestions based on metrics and patterns"""
        suggestions = []
        
        if not metrics:
            return suggestions
        
        try:
            # Slow execution time suggestion
            if metrics.average_execution_time_ms > 100:
                suggestions.append(OptimizationSuggestion(
                    rule_id=rule_id,
                    suggestion_type="performance",
                    priority="high" if metrics.average_execution_time_ms > 500 else "medium",
                    description=f"Rule has slow average execution time ({metrics.average_execution_time_ms:.1f}ms). Consider optimizing conditions or actions.",
                    expected_improvement="30-50% faster execution",
                    implementation_effort="medium",
                    metadata={
                        "current_avg_time_ms": metrics.average_execution_time_ms,
                        "target_time_ms": 50
                    }
                ))
            
            # Low success rate suggestion
            if metrics.success_rate < 95:
                suggestions.append(OptimizationSuggestion(
                    rule_id=rule_id,
                    suggestion_type="reliability",
                    priority="high",
                    description=f"Rule has low success rate ({metrics.success_rate:.1f}%). Review rule logic and error handling.",
                    expected_improvement="Improved reliability and fewer failures",
                    implementation_effort="medium",
                    metadata={
                        "current_success_rate": metrics.success_rate,
                        "failed_evaluations": metrics.failed_evaluations
                    }
                ))
            
            # Unused rule suggestion
            if metrics.usage_frequency < 0.1:  # Less than 0.1 evaluations per day
                suggestions.append(OptimizationSuggestion(
                    rule_id=rule_id,
                    suggestion_type="usage",
                    priority="low",
                    description="Rule is rarely used. Consider archiving or reviewing its necessity.",
                    expected_improvement="Reduced system complexity",
                    implementation_effort="low",
                    metadata={
                        "usage_frequency": metrics.usage_frequency,
                        "total_evaluations": metrics.total_evaluations
                    }
                ))
            
            # High usage optimization
            if metrics.usage_frequency > 10:  # More than 10 evaluations per day
                suggestions.append(OptimizationSuggestion(
                    rule_id=rule_id,
                    suggestion_type="caching",
                    priority="medium",
                    description="Rule is frequently used. Consider adding caching or pre-computation.",
                    expected_improvement="Reduced load and faster response times",
                    implementation_effort="high",
                    metadata={
                        "usage_frequency": metrics.usage_frequency,
                        "total_evaluations": metrics.total_evaluations
                    }
                ))
            
            # Pattern-based suggestions
            if patterns:
                # Concentrated usage pattern
                if len(patterns.peak_usage_hours) <= 2:
                    suggestions.append(OptimizationSuggestion(
                        rule_id=rule_id,
                        suggestion_type="scheduling",
                        priority="low",
                        description="Rule usage is concentrated in specific hours. Consider pre-computation during low-usage periods.",
                        expected_improvement="Better resource utilization",
                        implementation_effort="medium",
                        metadata={
                            "peak_hours": patterns.peak_usage_hours
                        }
                    ))
                
                # Machine-specific usage
                if len(patterns.usage_by_machine) == 1:
                    machine_id = list(patterns.usage_by_machine.keys())[0]
                    suggestions.append(OptimizationSuggestion(
                        rule_id=rule_id,
                        suggestion_type="scope",
                        priority="low",
                        description=f"Rule is only used on machine '{machine_id}'. Consider machine-specific scope.",
                        expected_improvement="Better rule organization",
                        implementation_effort="low",
                        metadata={
                            "primary_machine": machine_id
                        }
                    ))
            
        except Exception as e:
            print(f"Error generating optimization suggestions for {rule_id}: {e}")
        
        return suggestions
    
    def _generate_rule_optimization_suggestions(self, rule_data) -> List[OptimizationSuggestion]:
        """Generate optimization suggestions for a rule based on database data"""
        suggestions = []
        
        try:
            rule_id = rule_data['id']
            avg_time = rule_data['avg_time']
            max_time = rule_data['max_time']
            eval_count = rule_data['evaluation_count']
            
            # Performance suggestions
            if avg_time > 100:
                priority = "high" if avg_time > 500 else "medium"
                suggestions.append(OptimizationSuggestion(
                    rule_id=rule_id,
                    suggestion_type="performance",
                    priority=priority,
                    description=f"Rule '{rule_data['name']}' has slow execution ({avg_time:.1f}ms avg). Optimize conditions and actions.",
                    expected_improvement="30-50% performance improvement",
                    implementation_effort="medium",
                    metadata={"avg_time": avg_time, "max_time": max_time}
                ))
            
            # High variance suggestion
            if max_time > avg_time * 3:
                suggestions.append(OptimizationSuggestion(
                    rule_id=rule_id,
                    suggestion_type="consistency",
                    priority="medium",
                    description=f"Rule '{rule_data['name']}' has inconsistent execution times. Review for edge cases.",
                    expected_improvement="More predictable performance",
                    implementation_effort="medium",
                    metadata={"avg_time": avg_time, "max_time": max_time, "variance_ratio": max_time / avg_time}
                ))
            
            # Usage-based suggestions
            if eval_count < 10:  # Low usage in 30 days
                suggestions.append(OptimizationSuggestion(
                    rule_id=rule_id,
                    suggestion_type="usage",
                    priority="low",
                    description=f"Rule '{rule_data['name']}' is rarely used ({eval_count} evaluations in 30 days). Consider archiving.",
                    expected_improvement="Reduced system complexity",
                    implementation_effort="low",
                    metadata={"evaluation_count": eval_count}
                ))
            
        except Exception as e:
            print(f"Error generating suggestions for rule {rule_data.get('id', 'unknown')}: {e}")
        
        return suggestions
    
    def _calculate_performance_score(self, avg_time_ms: float, success_rate: float, usage_frequency: float) -> float:
        """Calculate a performance score (0-100) based on multiple factors"""
        try:
            # Speed score (0-40 points) - lower time is better
            if avg_time_ms <= 10:
                speed_score = 40
            elif avg_time_ms <= 50:
                speed_score = 35
            elif avg_time_ms <= 100:
                speed_score = 25
            elif avg_time_ms <= 500:
                speed_score = 15
            else:
                speed_score = 5
            
            # Reliability score (0-40 points) - higher success rate is better
            reliability_score = (success_rate / 100) * 40
            
            # Usage score (0-20 points) - moderate usage is optimal
            if 1 <= usage_frequency <= 10:
                usage_score = 20
            elif 0.1 <= usage_frequency < 1 or 10 < usage_frequency <= 50:
                usage_score = 15
            elif usage_frequency > 50:
                usage_score = 10  # Very high usage might indicate inefficiency
            else:
                usage_score = 5  # Very low usage
            
            total_score = speed_score + reliability_score + usage_score
            return min(100, max(0, total_score))  # Ensure score is between 0-100
            
        except Exception as e:
            print(f"Error calculating performance score: {e}")
            return 50  # Default neutral score
    
    def _get_priority_score(self, priority: str) -> int:
        """Convert priority string to numeric score for sorting"""
        priority_scores = {
            "high": 3,
            "medium": 2,
            "low": 1
        }
        return priority_scores.get(priority.lower(), 0)
    
    def get_rule_comparison(self, rule_ids: List[str], days: int = 30) -> Dict[str, Any]:
        """Compare performance metrics across multiple rules"""
        try:
            comparison_data = {}
            
            for rule_id in rule_ids:
                analytics = self.get_rule_analytics(rule_id, days)
                if analytics.get('performance_metrics'):
                    comparison_data[rule_id] = analytics['performance_metrics']
            
            if not comparison_data:
                return {"error": "No performance data available for comparison"}
            
            # Calculate comparative metrics
            avg_times = [data['average_execution_time_ms'] for data in comparison_data.values()]
            success_rates = [data['success_rate'] for data in comparison_data.values()]
            usage_frequencies = [data['usage_frequency'] for data in comparison_data.values()]
            
            return {
                "rules_compared": len(comparison_data),
                "comparison_data": comparison_data,
                "summary": {
                    "fastest_rule": min(comparison_data.items(), key=lambda x: x[1]['average_execution_time_ms']),
                    "slowest_rule": max(comparison_data.items(), key=lambda x: x[1]['average_execution_time_ms']),
                    "most_reliable_rule": max(comparison_data.items(), key=lambda x: x[1]['success_rate']),
                    "most_used_rule": max(comparison_data.items(), key=lambda x: x[1]['usage_frequency']),
                    "average_execution_time_ms": statistics.mean(avg_times),
                    "average_success_rate": statistics.mean(success_rates),
                    "average_usage_frequency": statistics.mean(usage_frequencies)
                },
                "analysis_period_days": days,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error comparing rules: {e}")
            return {"error": str(e)}
    
    def get_performance_trends(self, rule_id: str, days: int = 30) -> Dict[str, Any]:
        """Get performance trends over time for a rule"""
        try:
            with sqlite3.connect(self.rules_db.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                cursor = conn.execute("""
                    SELECT DATE(created_at) as date,
                           COUNT(*) as evaluations,
                           AVG(execution_time_ms) as avg_time,
                           MIN(execution_time_ms) as min_time,
                           MAX(execution_time_ms) as max_time
                    FROM rule_evaluations 
                    WHERE rule_id = ? AND created_at > datetime('now', '-{} days')
                    GROUP BY DATE(created_at)
                    ORDER BY date
                """.format(days), (rule_id,))
                
                daily_data = cursor.fetchall()
                
                if not daily_data:
                    return {"error": "No trend data available"}
                
                # Calculate trends
                dates = [row['date'] for row in daily_data]
                avg_times = [row['avg_time'] for row in daily_data]
                evaluation_counts = [row['evaluations'] for row in daily_data]
                
                # Simple trend calculation (positive = improving, negative = degrading)
                if len(avg_times) >= 2:
                    time_trend = (avg_times[-1] - avg_times[0]) / len(avg_times)
                    usage_trend = (evaluation_counts[-1] - evaluation_counts[0]) / len(evaluation_counts)
                else:
                    time_trend = 0
                    usage_trend = 0
                
                return {
                    "rule_id": rule_id,
                    "daily_data": [dict(row) for row in daily_data],
                    "trends": {
                        "performance_trend": "improving" if time_trend < -5 else "degrading" if time_trend > 5 else "stable",
                        "usage_trend": "increasing" if usage_trend > 0.5 else "decreasing" if usage_trend < -0.5 else "stable",
                        "time_trend_ms_per_day": time_trend,
                        "usage_trend_evals_per_day": usage_trend
                    },
                    "analysis_period_days": days,
                    "generated_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            print(f"Error getting performance trends for {rule_id}: {e}")
            return {"error": str(e)}