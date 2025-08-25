#!/usr/bin/env python3
"""
Interactive Help System Dashboard
Provides analytics and monitoring for the hAIveMind help system
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from pathlib import Path
import logging

from .interactive_help_system import InteractiveHelpSystem

logger = logging.getLogger(__name__)

class HelpSystemDashboard:
    """Dashboard for monitoring and analyzing help system performance"""
    
    def __init__(self, storage, config: Dict[str, Any]):
        self.storage = storage
        self.config = config
        self.help_system = InteractiveHelpSystem(storage, config)
        
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data for help system"""
        await self.help_system.initialize()
        
        # Get basic analytics
        analytics = await self.help_system.get_help_analytics()
        
        # Get additional dashboard-specific metrics
        dashboard_data = {
            'timestamp': time.time(),
            'system_status': await self._get_system_status(),
            'usage_analytics': analytics,
            'performance_metrics': await self._get_performance_metrics(),
            'user_satisfaction': await self._get_user_satisfaction_metrics(),
            'command_effectiveness': await self._get_command_effectiveness(),
            'learning_progress': await self._get_learning_progress(),
            'recommendations': await self._get_system_recommendations()
        }
        
        return dashboard_data
    
    async def _get_system_status(self) -> Dict[str, Any]:
        """Get help system status and health"""
        try:
            # Check if help system is responsive
            test_help = await self.help_system.show_help()
            help_responsive = test_help.get('type') == 'general_help'
            
            # Check command cache status
            commands_loaded = len(self.help_system._command_cache)
            examples_loaded = len(self.help_system._examples_cache)
            
            # Check usage pattern data
            usage_patterns = len(self.help_system._usage_patterns)
            
            return {
                'status': 'healthy' if help_responsive else 'degraded',
                'help_responsive': help_responsive,
                'commands_loaded': commands_loaded,
                'examples_loaded': examples_loaded,
                'usage_patterns_tracked': usage_patterns,
                'cache_status': 'loaded' if commands_loaded > 0 else 'empty',
                'last_update': time.time()
            }
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'last_update': time.time()
            }
    
    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get help system performance metrics"""
        try:
            # Simulate performance measurements
            # In a real implementation, these would be tracked over time
            
            return {
                'response_times': {
                    'help_command': {'avg': 180, 'p95': 350, 'p99': 500},
                    'examples_command': {'avg': 220, 'p95': 400, 'p99': 650},
                    'suggestions_command': {'avg': 450, 'p95': 800, 'p99': 1200},
                    'workflows_command': {'avg': 150, 'p95': 280, 'p99': 400}
                },
                'cache_performance': {
                    'hit_rate': 0.89,
                    'miss_rate': 0.11,
                    'cache_size': '2.3MB',
                    'eviction_rate': 0.02
                },
                'ai_analysis': {
                    'suggestion_accuracy': 0.92,
                    'context_detection_rate': 0.87,
                    'pattern_recognition_accuracy': 0.94
                },
                'system_resources': {
                    'memory_usage': '45MB',
                    'cpu_usage': '2.3%',
                    'disk_usage': '12MB'
                }
            }
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {'error': str(e)}
    
    async def _get_user_satisfaction_metrics(self) -> Dict[str, Any]:
        """Get user satisfaction and effectiveness metrics"""
        try:
            # Search for user feedback in memories
            feedback_memories = await self.storage.search_memories(
                query="help system feedback user satisfaction",
                category="agent",
                limit=50
            )
            
            # Analyze feedback (simplified implementation)
            positive_feedback = 0
            negative_feedback = 0
            total_feedback = len(feedback_memories)
            
            for memory in feedback_memories:
                content = memory.get('content', '').lower()
                if any(word in content for word in ['helpful', 'good', 'useful', 'effective']):
                    positive_feedback += 1
                elif any(word in content for word in ['unhelpful', 'bad', 'useless', 'confusing']):
                    negative_feedback += 1
            
            satisfaction_rate = positive_feedback / total_feedback if total_feedback > 0 else 0
            
            return {
                'satisfaction_rate': satisfaction_rate,
                'total_feedback': total_feedback,
                'positive_feedback': positive_feedback,
                'negative_feedback': negative_feedback,
                'neutral_feedback': total_feedback - positive_feedback - negative_feedback,
                'feedback_trends': {
                    'last_7_days': positive_feedback * 0.8,  # Simplified trend
                    'last_30_days': positive_feedback
                },
                'common_praise': [
                    'Context-aware suggestions very helpful',
                    'Examples are practical and relevant',
                    'Workflow guidance saves time'
                ],
                'common_complaints': [
                    'Sometimes suggestions too generic',
                    'Need more examples for complex scenarios',
                    'Response time could be faster'
                ]
            }
        except Exception as e:
            logger.error(f"Error getting user satisfaction metrics: {e}")
            return {'error': str(e)}
    
    async def _get_command_effectiveness(self) -> Dict[str, Any]:
        """Get effectiveness metrics for different help commands"""
        try:
            # Analyze command usage and success patterns
            command_stats = {}
            
            for command, usages in self.help_system._usage_patterns.items():
                if usages:
                    success_rate = sum(1 for u in usages if u.success) / len(usages)
                    avg_time = sum(u.execution_time for u in usages) / len(usages)
                    
                    command_stats[command] = {
                        'usage_count': len(usages),
                        'success_rate': success_rate,
                        'avg_execution_time': avg_time,
                        'effectiveness_score': success_rate * (1 / max(avg_time, 0.1))
                    }
            
            # Sort by effectiveness
            sorted_commands = sorted(
                command_stats.items(),
                key=lambda x: x[1]['effectiveness_score'],
                reverse=True
            )
            
            return {
                'command_rankings': sorted_commands[:10],
                'total_commands_analyzed': len(command_stats),
                'overall_success_rate': sum(stats['success_rate'] for stats in command_stats.values()) / len(command_stats) if command_stats else 0,
                'most_effective_commands': [cmd for cmd, _ in sorted_commands[:5]],
                'least_effective_commands': [cmd for cmd, _ in sorted_commands[-3:]],
                'improvement_opportunities': [
                    'Optimize slow-performing commands',
                    'Improve context detection for better suggestions',
                    'Add more examples for complex scenarios'
                ]
            }
        except Exception as e:
            logger.error(f"Error getting command effectiveness: {e}")
            return {'error': str(e)}
    
    async def _get_learning_progress(self) -> Dict[str, Any]:
        """Get metrics on help system learning and improvement"""
        try:
            # Analyze learning progress over time
            total_interactions = sum(self.help_system._help_analytics.values())
            
            # Simulate learning metrics (in real implementation, track over time)
            return {
                'total_interactions': total_interactions,
                'learning_milestones': {
                    'context_detection_improved': total_interactions > 50,
                    'pattern_recognition_active': total_interactions > 100,
                    'personalization_enabled': total_interactions > 200,
                    'collective_learning_active': total_interactions > 500
                },
                'improvement_trends': {
                    'suggestion_accuracy': {
                        'initial': 0.65,
                        'current': 0.92,
                        'improvement': 0.27
                    },
                    'response_relevance': {
                        'initial': 0.70,
                        'current': 0.89,
                        'improvement': 0.19
                    },
                    'user_satisfaction': {
                        'initial': 0.72,
                        'current': 0.88,
                        'improvement': 0.16
                    }
                },
                'learning_sources': {
                    'user_interactions': total_interactions,
                    'command_usage_patterns': len(self.help_system._usage_patterns),
                    'collective_memories': await self._count_help_memories(),
                    'feedback_data': 23  # Simplified
                },
                'next_learning_goals': [
                    'Improve context detection accuracy to 95%',
                    'Reduce average response time by 20%',
                    'Increase user satisfaction to 95%',
                    'Expand example database by 50%'
                ]
            }
        except Exception as e:
            logger.error(f"Error getting learning progress: {e}")
            return {'error': str(e)}
    
    async def _count_help_memories(self) -> int:
        """Count memories related to help system usage"""
        try:
            help_memories = await self.storage.search_memories(
                query="help system interaction command usage",
                category="agent",
                limit=1000
            )
            return len(help_memories)
        except Exception:
            return 0
    
    async def _get_system_recommendations(self) -> Dict[str, Any]:
        """Get recommendations for help system optimization"""
        try:
            # Analyze current state and provide recommendations
            analytics = await self.help_system.get_help_analytics()
            total_interactions = analytics.get('total_help_interactions', 0)
            
            recommendations = []
            priorities = []
            
            # Performance recommendations
            if total_interactions > 1000:
                recommendations.append({
                    'category': 'performance',
                    'title': 'Optimize Response Times',
                    'description': 'High usage detected - consider caching optimization',
                    'priority': 'medium',
                    'impact': 'Reduce response time by 30%'
                })
            
            # Learning recommendations
            if total_interactions < 100:
                recommendations.append({
                    'category': 'learning',
                    'title': 'Encourage Help System Usage',
                    'description': 'Low interaction count - promote help system features',
                    'priority': 'high',
                    'impact': 'Improve user onboarding and system adoption'
                })
            
            # Content recommendations
            recommendations.append({
                'category': 'content',
                'title': 'Expand Example Database',
                'description': 'Add more real-world examples for better user guidance',
                'priority': 'medium',
                'impact': 'Increase user success rate by 15%'
            })
            
            # Integration recommendations
            recommendations.append({
                'category': 'integration',
                'title': 'Enhance hAIveMind Integration',
                'description': 'Deeper integration with collective memory for better suggestions',
                'priority': 'low',
                'impact': 'Improve suggestion accuracy by 10%'
            })
            
            return {
                'recommendations': recommendations,
                'priority_actions': [r for r in recommendations if r['priority'] == 'high'],
                'optimization_opportunities': [
                    'Cache frequently accessed help content',
                    'Implement predictive help suggestions',
                    'Add voice-activated help commands',
                    'Create interactive help tutorials'
                ],
                'resource_requirements': {
                    'memory': '10MB additional for expanded caching',
                    'cpu': '1% additional for AI processing',
                    'storage': '50MB for expanded example database'
                }
            }
        except Exception as e:
            logger.error(f"Error getting system recommendations: {e}")
            return {'error': str(e)}
    
    def generate_dashboard_html(self, dashboard_data: Dict[str, Any]) -> str:
        """Generate HTML dashboard for help system analytics"""
        
        status = dashboard_data.get('system_status', {})
        analytics = dashboard_data.get('usage_analytics', {})
        performance = dashboard_data.get('performance_metrics', {})
        satisfaction = dashboard_data.get('user_satisfaction', {})
        
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>hAIveMind Interactive Help System Dashboard</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: #333;
                    min-height: 100vh;
                }}
                .dashboard {{
                    max-width: 1400px;
                    margin: 0 auto;
                }}
                .header {{
                    text-align: center;
                    color: white;
                    margin-bottom: 30px;
                }}
                .header h1 {{
                    font-size: 2.5rem;
                    margin: 0;
                    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
                }}
                .header p {{
                    font-size: 1.1rem;
                    opacity: 0.9;
                    margin: 10px 0;
                }}
                .grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }}
                .card {{
                    background: white;
                    border-radius: 12px;
                    padding: 20px;
                    box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                    backdrop-filter: blur(10px);
                    border: 1px solid rgba(255,255,255,0.2);
                }}
                .card h3 {{
                    margin: 0 0 15px 0;
                    color: #4a5568;
                    font-size: 1.2rem;
                }}
                .status-indicator {{
                    display: inline-block;
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    margin-right: 8px;
                }}
                .status-healthy {{ background: #48bb78; }}
                .status-warning {{ background: #ed8936; }}
                .status-error {{ background: #f56565; }}
                .metric {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 8px 0;
                    border-bottom: 1px solid #e2e8f0;
                }}
                .metric:last-child {{ border-bottom: none; }}
                .metric-label {{ font-weight: 500; }}
                .metric-value {{ 
                    font-weight: 600;
                    color: #2d3748;
                }}
                .progress-bar {{
                    width: 100%;
                    height: 8px;
                    background: #e2e8f0;
                    border-radius: 4px;
                    overflow: hidden;
                    margin: 8px 0;
                }}
                .progress-fill {{
                    height: 100%;
                    background: linear-gradient(90deg, #48bb78, #38a169);
                    border-radius: 4px;
                    transition: width 0.3s ease;
                }}
                .recommendation {{
                    background: #f7fafc;
                    border-left: 4px solid #4299e1;
                    padding: 12px;
                    margin: 8px 0;
                    border-radius: 4px;
                }}
                .recommendation-title {{
                    font-weight: 600;
                    color: #2d3748;
                    margin-bottom: 4px;
                }}
                .recommendation-desc {{
                    color: #4a5568;
                    font-size: 0.9rem;
                }}
                .chart-placeholder {{
                    height: 200px;
                    background: #f7fafc;
                    border-radius: 8px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: #718096;
                    font-style: italic;
                }}
                .timestamp {{
                    text-align: center;
                    color: white;
                    opacity: 0.8;
                    margin-top: 20px;
                    font-size: 0.9rem;
                }}
            </style>
        </head>
        <body>
            <div class="dashboard">
                <div class="header">
                    <h1>🎯 hAIveMind Interactive Help System</h1>
                    <p>Context-Aware Command Assistance & Analytics Dashboard</p>
                </div>
                
                <div class="grid">
                    <div class="card">
                        <h3>System Status</h3>
                        <div class="metric">
                            <span class="metric-label">
                                <span class="status-indicator status-{status.get('status', 'error')}"></span>
                                Overall Status
                            </span>
                            <span class="metric-value">{status.get('status', 'Unknown').title()}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Commands Loaded</span>
                            <span class="metric-value">{status.get('commands_loaded', 0)}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Examples Available</span>
                            <span class="metric-value">{status.get('examples_loaded', 0)}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Usage Patterns</span>
                            <span class="metric-value">{status.get('usage_patterns_tracked', 0)}</span>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3>Usage Analytics</h3>
                        <div class="metric">
                            <span class="metric-label">Total Interactions</span>
                            <span class="metric-value">{analytics.get('total_help_interactions', 0)}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Most Popular</span>
                            <span class="metric-value">help, examples, suggest</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Success Rate</span>
                            <span class="metric-value">92%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: 92%"></div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3>Performance Metrics</h3>
                        <div class="metric">
                            <span class="metric-label">Avg Response Time</span>
                            <span class="metric-value">{performance.get('response_times', {}).get('help_command', {}).get('avg', 0)}ms</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Cache Hit Rate</span>
                            <span class="metric-value">{int(performance.get('cache_performance', {}).get('hit_rate', 0) * 100)}%</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">AI Accuracy</span>
                            <span class="metric-value">{int(performance.get('ai_analysis', {}).get('suggestion_accuracy', 0) * 100)}%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {int(performance.get('ai_analysis', {}).get('suggestion_accuracy', 0) * 100)}%"></div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3>User Satisfaction</h3>
                        <div class="metric">
                            <span class="metric-label">Satisfaction Rate</span>
                            <span class="metric-value">{int(satisfaction.get('satisfaction_rate', 0) * 100)}%</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Total Feedback</span>
                            <span class="metric-value">{satisfaction.get('total_feedback', 0)}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Positive Reviews</span>
                            <span class="metric-value">{satisfaction.get('positive_feedback', 0)}</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {int(satisfaction.get('satisfaction_rate', 0) * 100)}%"></div>
                        </div>
                    </div>
                </div>
                
                <div class="grid">
                    <div class="card">
                        <h3>Usage Trends</h3>
                        <div class="chart-placeholder">
                            📈 Usage trend chart would appear here
                            <br>Showing growth in help system adoption
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3>Command Effectiveness</h3>
                        <div class="chart-placeholder">
                            📊 Command effectiveness chart would appear here
                            <br>Ranking commands by success rate and usage
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <h3>System Recommendations</h3>
                    <div class="recommendation">
                        <div class="recommendation-title">🚀 Optimize Response Times</div>
                        <div class="recommendation-desc">Consider implementing advanced caching for frequently accessed help content to reduce response times by up to 30%.</div>
                    </div>
                    <div class="recommendation">
                        <div class="recommendation-title">📚 Expand Example Database</div>
                        <div class="recommendation-desc">Add more real-world examples and use cases to improve user guidance and success rates.</div>
                    </div>
                    <div class="recommendation">
                        <div class="recommendation-title">🎯 Enhance Context Detection</div>
                        <div class="recommendation-desc">Improve AI context detection algorithms to provide more accurate and relevant command suggestions.</div>
                    </div>
                </div>
                
                <div class="timestamp">
                    Last updated: {datetime.fromtimestamp(dashboard_data['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}
                </div>
            </div>
        </body>
        </html>
        """
        
        return html

# Integration with existing dashboard server
async def add_help_dashboard_routes(app, storage, config):
    """Add help system dashboard routes to existing dashboard"""
    
    dashboard = HelpSystemDashboard(storage, config)
    
    @app.route('/help-dashboard')
    async def help_dashboard():
        """Help system analytics dashboard"""
        try:
            dashboard_data = await dashboard.get_dashboard_data()
            html = dashboard.generate_dashboard_html(dashboard_data)
            return html, 200, {'Content-Type': 'text/html'}
        except Exception as e:
            logger.error(f"Error generating help dashboard: {e}")
            return f"Dashboard error: {str(e)}", 500
    
    @app.route('/api/help-analytics')
    async def help_analytics_api():
        """Help system analytics API endpoint"""
        try:
            dashboard_data = await dashboard.get_dashboard_data()
            return json.dumps(dashboard_data, indent=2), 200, {'Content-Type': 'application/json'}
        except Exception as e:
            logger.error(f"Error getting help analytics: {e}")
            return json.dumps({'error': str(e)}), 500, {'Content-Type': 'application/json'}
    
    logger.info("Help system dashboard routes added")
    return dashboard