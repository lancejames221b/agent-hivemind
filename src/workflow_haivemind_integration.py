#!/usr/bin/env python3
"""
hAIveMind Integration for Workflow Automation
Provides intelligent learning and awareness integration with the collective memory system
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import logging
import re

from .workflow_automation_engine import WorkflowAutomationEngine, WorkflowStatus, WorkflowExecution, WorkflowTemplate

logger = logging.getLogger(__name__)

class WorkflowhAIveMindIntegration:
    """Integration layer between workflow automation and hAIveMind collective memory"""
    
    def __init__(self, workflow_engine: WorkflowAutomationEngine, storage, config: Dict[str, Any]):
        self.workflow_engine = workflow_engine
        self.storage = storage
        self.config = config
        
        # Learning and pattern recognition
        self.pattern_analyzer = WorkflowPatternAnalyzer(storage)
        self.success_predictor = WorkflowSuccessPredictor(storage)
        self.context_detector = WorkflowContextDetector(storage)
        
        # Collective intelligence features
        self.collective_learner = CollectiveLearner(storage)
        self.knowledge_sharer = WorkflowKnowledgeSharer(storage)
        self.adaptive_optimizer = AdaptiveWorkflowOptimizer(storage)
        
        # Real-time monitoring
        self.execution_monitor = WorkflowExecutionMonitor(storage)
        self.performance_tracker = WorkflowPerformanceTracker(storage)
        
        # Integration state
        self._learning_enabled = config.get('workflow_learning', {}).get('enabled', True)
        self._sharing_enabled = config.get('workflow_sharing', {}).get('enabled', True)
        self._optimization_enabled = config.get('workflow_optimization', {}).get('enabled', True)
    
    async def initialize(self):
        """Initialize hAIveMind integration"""
        await self.pattern_analyzer.initialize()
        await self.success_predictor.initialize()
        await self.context_detector.initialize()
        await self.collective_learner.initialize()
        await self.knowledge_sharer.initialize()
        await self.adaptive_optimizer.initialize()
        
        # Register workflow execution hooks
        self._register_execution_hooks()
        
        logger.info("Workflow hAIveMind integration initialized")
    
    def _register_execution_hooks(self):
        """Register hooks for workflow execution events"""
        # This would integrate with the workflow engine's event system
        # For now, we'll implement manual integration points
        pass
    
    async def on_workflow_start(self, execution: WorkflowExecution):
        """Handle workflow execution start"""
        if not self._learning_enabled:
            return
        
        # Store execution start in collective memory
        await self.storage.store_memory(
            content=f"Workflow execution started: {execution.name}",
            category="agent",
            context=f"Workflow automation - execution start",
            metadata={
                'workflow_execution_start': json.dumps({
                    'execution_id': execution.id,
                    'template_id': execution.template_id,
                    'name': execution.name,
                    'trigger_type': execution.trigger_type.value,
                    'trigger_context': execution.trigger_context,
                    'parameters': execution.parameters,
                    'start_time': execution.start_time,
                    'machine_id': execution.machine_id,
                    'user_id': execution.user_id
                }),
                'event_type': 'workflow_start',
                'execution_id': execution.id,
                'template_id': execution.template_id,
                'agent_id': getattr(self.storage, 'agent_id', 'unknown'),
                'machine_id': getattr(self.storage, 'machine_id', 'unknown')
            },
            tags=['workflow', 'execution', 'started', execution.template_id, 'haivemind-learning']
        )
        
        # Analyze context and patterns
        await self.context_detector.analyze_execution_context(execution)
        
        # Share workflow start with collective if significant
        if execution.trigger_type.value in ['monitoring_alert', 'external_api']:
            await self.knowledge_sharer.share_workflow_event(execution, 'started')
    
    async def on_workflow_complete(self, execution: WorkflowExecution):
        """Handle workflow execution completion"""
        if not self._learning_enabled:
            return
        
        template = self.workflow_engine.templates.get(execution.template_id)
        if not template:
            return
        
        duration = (execution.end_time or time.time()) - execution.start_time
        success_rate = len(execution.completed_steps) / len(template.steps) if template.steps else 0
        
        # Store completion in collective memory
        await self.storage.store_memory(
            content=f"Workflow execution completed: {execution.name} in {duration:.1f}s with {success_rate:.0%} success",
            category="agent",
            context=f"Workflow automation - execution complete",
            metadata={
                'workflow_execution_complete': json.dumps({
                    'execution_id': execution.id,
                    'template_id': execution.template_id,
                    'name': execution.name,
                    'status': execution.status.value,
                    'duration': duration,
                    'success_rate': success_rate,
                    'completed_steps': len(execution.completed_steps),
                    'failed_steps': len(execution.failed_steps),
                    'total_steps': len(template.steps),
                    'trigger_type': execution.trigger_type.value,
                    'parameters': execution.parameters,
                    'step_results': execution.step_results,
                    'end_time': execution.end_time
                }),
                'event_type': 'workflow_complete',
                'execution_id': execution.id,
                'template_id': execution.template_id,
                'success_rate': success_rate,
                'duration': duration,
                'agent_id': getattr(self.storage, 'agent_id', 'unknown'),
                'machine_id': getattr(self.storage, 'machine_id', 'unknown')
            },
            tags=['workflow', 'execution', 'completed', execution.template_id, 'haivemind-learning']
        )
        
        # Learn from execution
        await self.collective_learner.learn_from_execution(execution, template)
        
        # Update success predictor
        await self.success_predictor.update_predictions(execution, template)
        
        # Share successful patterns
        if execution.status == WorkflowStatus.COMPLETED and success_rate > 0.8:
            await self.knowledge_sharer.share_successful_pattern(execution, template)
        
        # Optimize workflow if needed
        if self._optimization_enabled:
            await self.adaptive_optimizer.analyze_for_optimization(execution, template)
    
    async def on_workflow_fail(self, execution: WorkflowExecution):
        """Handle workflow execution failure"""
        if not self._learning_enabled:
            return
        
        template = self.workflow_engine.templates.get(execution.template_id)
        if not template:
            return
        
        duration = (execution.end_time or time.time()) - execution.start_time
        
        # Store failure in collective memory
        await self.storage.store_memory(
            content=f"Workflow execution failed: {execution.name} after {duration:.1f}s - {execution.error_message}",
            category="incidents",
            context=f"Workflow automation - execution failure",
            metadata={
                'workflow_execution_failure': json.dumps({
                    'execution_id': execution.id,
                    'template_id': execution.template_id,
                    'name': execution.name,
                    'error_message': execution.error_message,
                    'duration': duration,
                    'completed_steps': len(execution.completed_steps),
                    'failed_steps': len(execution.failed_steps),
                    'total_steps': len(template.steps),
                    'trigger_type': execution.trigger_type.value,
                    'parameters': execution.parameters,
                    'failure_point': execution.current_step,
                    'end_time': execution.end_time
                }),
                'event_type': 'workflow_failure',
                'execution_id': execution.id,
                'template_id': execution.template_id,
                'error_type': 'workflow_failure',
                'agent_id': getattr(self.storage, 'agent_id', 'unknown'),
                'machine_id': getattr(self.storage, 'machine_id', 'unknown')
            },
            tags=['workflow', 'execution', 'failed', execution.template_id, 'incident', 'haivemind-learning']
        )
        
        # Learn from failure
        await self.collective_learner.learn_from_failure(execution, template)
        
        # Share failure patterns to prevent recurrence
        await self.knowledge_sharer.share_failure_pattern(execution, template)
        
        # Analyze for improvements
        await self.adaptive_optimizer.analyze_failure_for_improvement(execution, template)
    
    async def enhance_workflow_suggestions(self, suggestions: List, context: Optional[str] = None,
                                         recent_commands: Optional[List[str]] = None) -> List:
        """Enhance workflow suggestions with hAIveMind intelligence"""
        if not self._learning_enabled:
            return suggestions
        
        # Get collective intelligence insights
        collective_insights = await self.collective_learner.get_collective_insights(context, recent_commands)
        
        # Enhance each suggestion
        enhanced_suggestions = []
        for suggestion in suggestions:
            # Get success probability from collective experience
            success_prob = await self.success_predictor.predict_success(
                suggestion.workflow_id, context, recent_commands
            )
            
            # Get similar execution patterns
            similar_patterns = await self.pattern_analyzer.find_similar_patterns(
                suggestion.workflow_id, context
            )
            
            # Update suggestion with collective intelligence
            suggestion.success_probability = max(suggestion.success_probability, success_prob)
            suggestion.similar_executions = len(similar_patterns)
            
            # Add collective insights to reasoning
            if collective_insights.get(suggestion.workflow_id):
                insight = collective_insights[suggestion.workflow_id]
                suggestion.reason += f" | Collective insight: {insight}"
            
            enhanced_suggestions.append(suggestion)
        
        # Re-rank based on collective intelligence
        enhanced_suggestions.sort(
            key=lambda s: (s.confidence * 0.4 + s.success_probability * 0.6),
            reverse=True
        )
        
        return enhanced_suggestions
    
    async def get_workflow_recommendations(self, template_id: str) -> Dict[str, Any]:
        """Get hAIveMind-powered workflow recommendations"""
        template = self.workflow_engine.templates.get(template_id)
        if not template:
            return {}
        
        # Get collective performance data
        performance_data = await self.performance_tracker.get_template_performance(template_id)
        
        # Get optimization suggestions
        optimizations = await self.adaptive_optimizer.get_optimization_suggestions(template_id)
        
        # Get similar successful workflows
        similar_workflows = await self.pattern_analyzer.find_similar_successful_workflows(template_id)
        
        # Get failure patterns to avoid
        failure_patterns = await self.pattern_analyzer.get_failure_patterns(template_id)
        
        return {
            'performance_insights': performance_data,
            'optimization_suggestions': optimizations,
            'similar_successful_workflows': similar_workflows,
            'failure_patterns_to_avoid': failure_patterns,
            'collective_success_rate': performance_data.get('collective_success_rate', 0),
            'recommended_parameters': performance_data.get('optimal_parameters', {}),
            'best_execution_contexts': performance_data.get('successful_contexts', [])
        }
    
    async def learn_from_command_sequences(self, sequences: List[List[str]]) -> List[Dict[str, Any]]:
        """Learn workflow patterns from command sequences"""
        if not self._learning_enabled:
            return []
        
        learned_patterns = []
        
        for sequence in sequences:
            if len(sequence) < 2:
                continue
            
            # Analyze sequence for workflow potential
            pattern_analysis = await self.pattern_analyzer.analyze_command_sequence(sequence)
            
            if pattern_analysis['workflow_potential'] > 0.7:
                # Check if similar workflow already exists
                existing_workflows = await self._find_similar_workflows(sequence)
                
                if not existing_workflows:
                    # Suggest new workflow creation
                    workflow_suggestion = await self._generate_workflow_from_sequence(sequence, pattern_analysis)
                    learned_patterns.append(workflow_suggestion)
                    
                    # Store learning in collective memory
                    await self.storage.store_memory(
                        content=f"Learned potential workflow pattern from command sequence: {' → '.join(sequence)}",
                        category="agent",
                        context="Workflow pattern learning",
                        metadata={
                            'learned_pattern': json.dumps({
                                'sequence': sequence,
                                'analysis': pattern_analysis,
                                'workflow_suggestion': workflow_suggestion
                            }),
                            'pattern_type': 'command_sequence',
                            'workflow_potential': pattern_analysis['workflow_potential'],
                            'agent_id': getattr(self.storage, 'agent_id', 'unknown')
                        },
                        tags=['workflow', 'learning', 'pattern', 'haivemind-intelligence']
                    )
        
        return learned_patterns
    
    async def _find_similar_workflows(self, sequence: List[str]) -> List[str]:
        """Find workflows similar to command sequence"""
        similar_workflows = []
        
        for template_id, template in self.workflow_engine.templates.items():
            template_commands = [step.command for step in template.steps]
            similarity = self._calculate_sequence_similarity(sequence, template_commands)
            
            if similarity > 0.8:  # High similarity threshold
                similar_workflows.append(template_id)
        
        return similar_workflows
    
    def _calculate_sequence_similarity(self, seq1: List[str], seq2: List[str]) -> float:
        """Calculate similarity between two command sequences"""
        if not seq1 or not seq2:
            return 0.0
        
        # Use Jaccard similarity for now (could be enhanced with sequence alignment)
        set1 = set(seq1)
        set2 = set(seq2)
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    async def _generate_workflow_from_sequence(self, sequence: List[str], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate workflow suggestion from command sequence"""
        # Analyze sequence context and purpose
        context_analysis = await self.context_detector.analyze_sequence_context(sequence)
        
        # Generate workflow metadata
        workflow_name = self._generate_workflow_name(sequence, context_analysis)
        workflow_description = self._generate_workflow_description(sequence, context_analysis)
        workflow_category = context_analysis.get('category', 'custom')
        
        # Generate steps
        steps = []
        for i, command in enumerate(sequence):
            step = {
                'id': f'step_{i+1}',
                'command': command,
                'description': f'Execute {command}',
                'parameters': {},
                'depends_on': [f'step_{i}'] if i > 0 else [],
                'timeout_seconds': 300
            }
            steps.append(step)
        
        return {
            'type': 'learned_workflow',
            'name': workflow_name,
            'description': workflow_description,
            'category': workflow_category,
            'tags': context_analysis.get('tags', []),
            'steps': steps,
            'confidence': analysis['workflow_potential'],
            'source_sequence': sequence,
            'learning_context': context_analysis
        }
    
    def _generate_workflow_name(self, sequence: List[str], context: Dict[str, Any]) -> str:
        """Generate a descriptive workflow name"""
        # Extract key terms from sequence
        key_terms = []
        for command in sequence:
            if 'broadcast' in command:
                key_terms.append('Communication')
            elif 'delegate' in command:
                key_terms.append('Task Assignment')
            elif 'status' in command:
                key_terms.append('Status Check')
            elif 'sync' in command:
                key_terms.append('Synchronization')
            elif 'remember' in command:
                key_terms.append('Knowledge Storage')
            elif 'query' in command:
                key_terms.append('Information Retrieval')
        
        if key_terms:
            return f"{' & '.join(key_terms[:2])} Workflow"
        else:
            return f"Custom {len(sequence)}-Step Workflow"
    
    def _generate_workflow_description(self, sequence: List[str], context: Dict[str, Any]) -> str:
        """Generate a descriptive workflow description"""
        purpose = context.get('purpose', 'execute a sequence of commands')
        return f"Automated workflow to {purpose} using the sequence: {' → '.join(sequence)}"

class WorkflowPatternAnalyzer:
    """Analyzes workflow execution patterns for learning"""
    
    def __init__(self, storage):
        self.storage = storage
        self.patterns = defaultdict(list)
        self.sequence_patterns = defaultdict(int)
    
    async def initialize(self):
        """Initialize pattern analyzer"""
        await self._load_historical_patterns()
    
    async def _load_historical_patterns(self):
        """Load historical execution patterns from memory"""
        try:
            pattern_memories = await self.storage.search_memories(
                query="workflow execution pattern",
                category="agent",
                limit=500
            )
            
            for memory in pattern_memories:
                if 'execution_pattern' in memory.get('metadata', {}):
                    pattern_data = memory['metadata']['execution_pattern']
                    if isinstance(pattern_data, str):
                        try:
                            pattern_data = json.loads(pattern_data)
                        except:
                            continue
                    
                    template_id = pattern_data.get('template_id')
                    if template_id:
                        self.patterns[template_id].append(pattern_data)
        
        except Exception as e:
            logger.error(f"Error loading historical patterns: {e}")
    
    async def analyze_command_sequence(self, sequence: List[str]) -> Dict[str, Any]:
        """Analyze command sequence for workflow potential"""
        # Calculate workflow potential based on various factors
        potential_score = 0.0
        
        # Factor 1: Sequence length (optimal 2-8 steps)
        length_score = min(len(sequence) / 8.0, 1.0) if len(sequence) >= 2 else 0.0
        potential_score += length_score * 0.2
        
        # Factor 2: Command diversity
        unique_commands = len(set(sequence))
        diversity_score = unique_commands / len(sequence)
        potential_score += diversity_score * 0.3
        
        # Factor 3: Logical flow patterns
        flow_score = self._analyze_command_flow(sequence)
        potential_score += flow_score * 0.3
        
        # Factor 4: Common workflow patterns
        pattern_score = self._check_common_patterns(sequence)
        potential_score += pattern_score * 0.2
        
        return {
            'workflow_potential': min(potential_score, 1.0),
            'length_score': length_score,
            'diversity_score': diversity_score,
            'flow_score': flow_score,
            'pattern_score': pattern_score,
            'sequence_length': len(sequence),
            'unique_commands': unique_commands
        }
    
    def _analyze_command_flow(self, sequence: List[str]) -> float:
        """Analyze logical flow of commands"""
        flow_score = 0.0
        
        # Check for logical progressions
        logical_flows = [
            ['hv-status', 'hv-broadcast'],  # Check then communicate
            ['hv-query', 'hv-delegate'],    # Search then assign
            ['hv-broadcast', 'hv-status'],  # Communicate then verify
            ['remember', 'hv-broadcast'],   # Document then share
            ['hv-sync', 'hv-status']        # Sync then verify
        ]
        
        for i in range(len(sequence) - 1):
            current_cmd = sequence[i]
            next_cmd = sequence[i + 1]
            
            for flow in logical_flows:
                if len(flow) >= 2 and current_cmd == flow[0] and next_cmd == flow[1]:
                    flow_score += 0.5
        
        return min(flow_score / (len(sequence) - 1), 1.0) if len(sequence) > 1 else 0.0
    
    def _check_common_patterns(self, sequence: List[str]) -> float:
        """Check for common workflow patterns"""
        pattern_score = 0.0
        
        # Common patterns
        incident_pattern = ['hv-status', 'hv-broadcast', 'hv-delegate']
        maintenance_pattern = ['hv-sync', 'remember', 'hv-broadcast']
        knowledge_pattern = ['recall', 'hv-broadcast', 'hv-query']
        
        common_patterns = [incident_pattern, maintenance_pattern, knowledge_pattern]
        
        for pattern in common_patterns:
            similarity = self._calculate_pattern_similarity(sequence, pattern)
            pattern_score = max(pattern_score, similarity)
        
        return pattern_score
    
    def _calculate_pattern_similarity(self, seq1: List[str], seq2: List[str]) -> float:
        """Calculate similarity between sequences"""
        if not seq1 or not seq2:
            return 0.0
        
        # Simple subsequence matching
        matches = 0
        for i in range(len(seq1)):
            for j in range(len(seq2)):
                if seq1[i] == seq2[j]:
                    matches += 1
                    break
        
        return matches / max(len(seq1), len(seq2))
    
    async def find_similar_patterns(self, workflow_id: str, context: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find similar execution patterns"""
        similar_patterns = []
        
        if workflow_id in self.patterns:
            patterns = self.patterns[workflow_id]
            
            # Filter by context if provided
            if context:
                patterns = [p for p in patterns if context.lower() in str(p.get('context', '')).lower()]
            
            # Sort by recency and success
            patterns.sort(key=lambda p: (p.get('success', False), p.get('timestamp', 0)), reverse=True)
            similar_patterns = patterns[:10]  # Top 10 similar patterns
        
        return similar_patterns
    
    async def find_similar_successful_workflows(self, template_id: str) -> List[str]:
        """Find similar workflows with high success rates"""
        # This would analyze workflow structures and find similar ones
        # For now, return empty list
        return []
    
    async def get_failure_patterns(self, template_id: str) -> List[Dict[str, Any]]:
        """Get common failure patterns for a workflow"""
        failure_patterns = []
        
        try:
            # Search for failure memories
            failure_memories = await self.storage.search_memories(
                query=f"workflow execution failed {template_id}",
                category="incidents",
                limit=50
            )
            
            failure_reasons = Counter()
            failure_steps = Counter()
            
            for memory in failure_memories:
                metadata = memory.get('metadata', {})
                if 'workflow_execution_failure' in metadata:
                    failure_data = metadata['workflow_execution_failure']
                    if isinstance(failure_data, str):
                        try:
                            failure_data = json.loads(failure_data)
                        except:
                            continue
                    
                    error_msg = failure_data.get('error_message', '')
                    failure_step = failure_data.get('failure_point', '')
                    
                    if error_msg:
                        failure_reasons[error_msg] += 1
                    if failure_step:
                        failure_steps[failure_step] += 1
            
            # Convert to pattern format
            for reason, count in failure_reasons.most_common(5):
                failure_patterns.append({
                    'type': 'error_message',
                    'pattern': reason,
                    'frequency': count,
                    'recommendation': f"Check for conditions that cause: {reason}"
                })
            
            for step, count in failure_steps.most_common(3):
                failure_patterns.append({
                    'type': 'failure_step',
                    'pattern': step,
                    'frequency': count,
                    'recommendation': f"Review step '{step}' for reliability issues"
                })
        
        except Exception as e:
            logger.error(f"Error getting failure patterns: {e}")
        
        return failure_patterns

class WorkflowSuccessPredictor:
    """Predicts workflow success probability based on collective experience"""
    
    def __init__(self, storage):
        self.storage = storage
        self.success_models = {}
    
    async def initialize(self):
        """Initialize success predictor"""
        await self._build_success_models()
    
    async def _build_success_models(self):
        """Build success prediction models from historical data"""
        try:
            # Get execution history
            execution_memories = await self.storage.search_memories(
                query="workflow execution",
                category="agent",
                limit=1000
            )
            
            # Group by template
            template_data = defaultdict(list)
            
            for memory in execution_memories:
                metadata = memory.get('metadata', {})
                template_id = metadata.get('template_id')
                
                if template_id and 'workflow_execution_complete' in metadata:
                    exec_data = metadata['workflow_execution_complete']
                    if isinstance(exec_data, str):
                        try:
                            exec_data = json.loads(exec_data)
                        except:
                            continue
                    
                    template_data[template_id].append(exec_data)
            
            # Build simple success models
            for template_id, executions in template_data.items():
                if len(executions) >= 3:  # Need minimum data
                    success_rate = sum(1 for e in executions if e.get('success_rate', 0) > 0.8) / len(executions)
                    avg_duration = sum(e.get('duration', 0) for e in executions) / len(executions)
                    
                    self.success_models[template_id] = {
                        'base_success_rate': success_rate,
                        'avg_duration': avg_duration,
                        'sample_size': len(executions),
                        'last_updated': time.time()
                    }
        
        except Exception as e:
            logger.error(f"Error building success models: {e}")
    
    async def predict_success(self, template_id: str, context: Optional[str] = None,
                            recent_commands: Optional[List[str]] = None) -> float:
        """Predict success probability for workflow execution"""
        base_probability = 0.5  # Default
        
        # Get base success rate from model
        if template_id in self.success_models:
            model = self.success_models[template_id]
            base_probability = model['base_success_rate']
            
            # Adjust based on sample size confidence
            confidence = min(model['sample_size'] / 10.0, 1.0)
            base_probability = base_probability * confidence + 0.5 * (1 - confidence)
        
        # Context-based adjustments
        context_adjustment = 0.0
        if context:
            # Higher success for planned activities
            if any(word in context.lower() for word in ['planned', 'scheduled', 'maintenance']):
                context_adjustment += 0.1
            
            # Lower success for emergency situations
            if any(word in context.lower() for word in ['emergency', 'critical', 'urgent']):
                context_adjustment -= 0.1
        
        # Recent commands pattern adjustment
        pattern_adjustment = 0.0
        if recent_commands:
            # If recent commands match workflow pattern, increase success
            # This would be more sophisticated in practice
            if len(recent_commands) >= 2:
                pattern_adjustment += 0.05
        
        final_probability = base_probability + context_adjustment + pattern_adjustment
        return max(0.0, min(1.0, final_probability))
    
    async def update_predictions(self, execution: WorkflowExecution, template: WorkflowTemplate):
        """Update prediction models based on execution results"""
        template_id = template.id
        success_rate = len(execution.completed_steps) / len(template.steps) if template.steps else 0
        duration = (execution.end_time or time.time()) - execution.start_time
        
        if template_id not in self.success_models:
            self.success_models[template_id] = {
                'base_success_rate': 0.5,
                'avg_duration': 0,
                'sample_size': 0,
                'last_updated': time.time()
            }
        
        model = self.success_models[template_id]
        
        # Update with exponential moving average
        alpha = 0.1  # Learning rate
        model['base_success_rate'] = (1 - alpha) * model['base_success_rate'] + alpha * (1.0 if success_rate > 0.8 else 0.0)
        model['avg_duration'] = (1 - alpha) * model['avg_duration'] + alpha * duration
        model['sample_size'] += 1
        model['last_updated'] = time.time()

class WorkflowContextDetector:
    """Detects and analyzes workflow execution contexts"""
    
    def __init__(self, storage):
        self.storage = storage
        self.context_patterns = {}
    
    async def initialize(self):
        """Initialize context detector"""
        await self._load_context_patterns()
    
    async def _load_context_patterns(self):
        """Load context patterns from memory"""
        # This would load learned context patterns
        pass
    
    async def analyze_execution_context(self, execution: WorkflowExecution):
        """Analyze context of workflow execution"""
        context_analysis = {
            'trigger_type': execution.trigger_type.value,
            'trigger_context': execution.trigger_context,
            'parameters': execution.parameters,
            'time_of_day': datetime.fromtimestamp(execution.start_time).hour if execution.start_time else None,
            'day_of_week': datetime.fromtimestamp(execution.start_time).weekday() if execution.start_time else None
        }
        
        # Store context analysis
        await self.storage.store_memory(
            content=f"Workflow context analysis for {execution.name}",
            category="agent",
            context="Workflow context analysis",
            metadata={
                'context_analysis': json.dumps(context_analysis),
                'execution_id': execution.id,
                'template_id': execution.template_id
            },
            tags=['workflow', 'context', 'analysis', 'haivemind-learning']
        )
        
        return context_analysis
    
    async def analyze_sequence_context(self, sequence: List[str]) -> Dict[str, Any]:
        """Analyze context of command sequence"""
        context = {
            'sequence_length': len(sequence),
            'commands': sequence,
            'category': 'custom',
            'purpose': 'execute commands',
            'tags': []
        }
        
        # Analyze command types
        if 'hv-broadcast' in sequence and 'hv-delegate' in sequence:
            context['category'] = 'incident_management'
            context['purpose'] = 'handle incidents and coordinate response'
            context['tags'].extend(['incident', 'coordination', 'response'])
        
        elif 'hv-sync' in sequence and 'remember' in sequence:
            context['category'] = 'maintenance'
            context['purpose'] = 'perform maintenance and document changes'
            context['tags'].extend(['maintenance', 'documentation', 'sync'])
        
        elif 'recall' in sequence and 'hv-query' in sequence:
            context['category'] = 'knowledge_management'
            context['purpose'] = 'search and share knowledge'
            context['tags'].extend(['knowledge', 'search', 'sharing'])
        
        return context

class CollectiveLearner:
    """Learns from collective workflow execution experiences"""
    
    def __init__(self, storage):
        self.storage = storage
        self.collective_insights = {}
    
    async def initialize(self):
        """Initialize collective learner"""
        await self._load_collective_insights()
    
    async def _load_collective_insights(self):
        """Load collective insights from memory"""
        try:
            insight_memories = await self.storage.search_memories(
                query="collective workflow insight",
                category="agent",
                limit=100
            )
            
            for memory in insight_memories:
                if 'collective_insight' in memory.get('metadata', {}):
                    insight_data = memory['metadata']['collective_insight']
                    if isinstance(insight_data, str):
                        try:
                            insight_data = json.loads(insight_data)
                        except:
                            continue
                    
                    workflow_id = insight_data.get('workflow_id')
                    if workflow_id:
                        self.collective_insights[workflow_id] = insight_data
        
        except Exception as e:
            logger.error(f"Error loading collective insights: {e}")
    
    async def learn_from_execution(self, execution: WorkflowExecution, template: WorkflowTemplate):
        """Learn from successful workflow execution"""
        if execution.status != WorkflowStatus.COMPLETED:
            return
        
        success_rate = len(execution.completed_steps) / len(template.steps) if template.steps else 0
        if success_rate < 0.8:
            return
        
        # Extract learning insights
        insights = {
            'workflow_id': template.id,
            'successful_parameters': execution.parameters,
            'optimal_context': execution.trigger_context,
            'execution_duration': (execution.end_time or time.time()) - execution.start_time,
            'success_factors': self._analyze_success_factors(execution, template),
            'timestamp': time.time()
        }
        
        # Store collective insight
        await self.storage.store_memory(
            content=f"Collective learning insight from successful {template.name} execution",
            category="agent",
            context="Collective workflow learning",
            metadata={
                'collective_insight': json.dumps(insights),
                'workflow_id': template.id,
                'learning_type': 'success_pattern',
                'agent_id': getattr(self.storage, 'agent_id', 'unknown')
            },
            tags=['workflow', 'collective-learning', 'success-pattern', template.id, 'haivemind-intelligence']
        )
        
        # Update local insights
        self.collective_insights[template.id] = insights
    
    async def learn_from_failure(self, execution: WorkflowExecution, template: WorkflowTemplate):
        """Learn from workflow execution failure"""
        # Extract failure insights
        insights = {
            'workflow_id': template.id,
            'failure_parameters': execution.parameters,
            'failure_context': execution.trigger_context,
            'failure_point': execution.current_step,
            'error_message': execution.error_message,
            'failure_factors': self._analyze_failure_factors(execution, template),
            'timestamp': time.time()
        }
        
        # Store failure learning
        await self.storage.store_memory(
            content=f"Collective learning insight from failed {template.name} execution",
            category="incidents",
            context="Collective workflow failure learning",
            metadata={
                'collective_failure_insight': json.dumps(insights),
                'workflow_id': template.id,
                'learning_type': 'failure_pattern',
                'agent_id': getattr(self.storage, 'agent_id', 'unknown')
            },
            tags=['workflow', 'collective-learning', 'failure-pattern', template.id, 'incident']
        )
    
    def _analyze_success_factors(self, execution: WorkflowExecution, template: WorkflowTemplate) -> List[str]:
        """Analyze factors that contributed to success"""
        factors = []
        
        # Analyze execution characteristics
        if execution.trigger_type.value == 'manual':
            factors.append('manual_execution')
        
        if execution.parameters:
            factors.append('parameterized_execution')
        
        # Analyze timing
        if execution.start_time:
            hour = datetime.fromtimestamp(execution.start_time).hour
            if 9 <= hour <= 17:
                factors.append('business_hours')
            else:
                factors.append('off_hours')
        
        return factors
    
    def _analyze_failure_factors(self, execution: WorkflowExecution, template: WorkflowTemplate) -> List[str]:
        """Analyze factors that contributed to failure"""
        factors = []
        
        if execution.error_message:
            if 'timeout' in execution.error_message.lower():
                factors.append('timeout_error')
            elif 'connection' in execution.error_message.lower():
                factors.append('connection_error')
            elif 'permission' in execution.error_message.lower():
                factors.append('permission_error')
        
        if execution.current_step:
            factors.append(f'failed_at_{execution.current_step}')
        
        return factors
    
    async def get_collective_insights(self, context: Optional[str] = None,
                                    recent_commands: Optional[List[str]] = None) -> Dict[str, str]:
        """Get collective insights for workflow suggestions"""
        insights = {}
        
        for workflow_id, insight_data in self.collective_insights.items():
            insight_text = f"Success rate improved by {insight_data.get('success_factors', [])}"
            insights[workflow_id] = insight_text
        
        return insights

class WorkflowKnowledgeSharer:
    """Shares workflow knowledge across the hAIveMind collective"""
    
    def __init__(self, storage):
        self.storage = storage
    
    async def initialize(self):
        """Initialize knowledge sharer"""
        pass
    
    async def share_workflow_event(self, execution: WorkflowExecution, event_type: str):
        """Share significant workflow events with collective"""
        # This would integrate with hAIveMind broadcast system
        message = f"Workflow {event_type}: {execution.name} ({execution.template_id})"
        
        await self.storage.store_memory(
            content=message,
            category="agent",
            context="Workflow event sharing",
            metadata={
                'shared_event': json.dumps({
                    'execution_id': execution.id,
                    'template_id': execution.template_id,
                    'event_type': event_type,
                    'name': execution.name,
                    'trigger_type': execution.trigger_type.value
                }),
                'event_type': f'workflow_{event_type}',
                'template_id': execution.template_id,
                'shared_with_collective': True
            },
            tags=['workflow', 'sharing', event_type, execution.template_id, 'haivemind-broadcast']
        )
    
    async def share_successful_pattern(self, execution: WorkflowExecution, template: WorkflowTemplate):
        """Share successful workflow patterns"""
        success_rate = len(execution.completed_steps) / len(template.steps) if template.steps else 0
        duration = (execution.end_time or time.time()) - execution.start_time
        
        message = f"Successful workflow pattern: {template.name} completed with {success_rate:.0%} success in {duration:.1f}s"
        
        await self.storage.store_memory(
            content=message,
            category="agent",
            context="Successful workflow pattern sharing",
            metadata={
                'successful_pattern': json.dumps({
                    'template_id': template.id,
                    'name': template.name,
                    'success_rate': success_rate,
                    'duration': duration,
                    'parameters': execution.parameters,
                    'context': execution.trigger_context
                }),
                'pattern_type': 'successful_workflow',
                'template_id': template.id,
                'success_rate': success_rate
            },
            tags=['workflow', 'success-pattern', 'sharing', template.id, 'haivemind-knowledge']
        )
    
    async def share_failure_pattern(self, execution: WorkflowExecution, template: WorkflowTemplate):
        """Share failure patterns to prevent recurrence"""
        message = f"Workflow failure pattern: {template.name} failed at {execution.current_step} - {execution.error_message}"
        
        await self.storage.store_memory(
            content=message,
            category="incidents",
            context="Workflow failure pattern sharing",
            metadata={
                'failure_pattern': json.dumps({
                    'template_id': template.id,
                    'name': template.name,
                    'failure_point': execution.current_step,
                    'error_message': execution.error_message,
                    'parameters': execution.parameters,
                    'context': execution.trigger_context
                }),
                'pattern_type': 'failure_workflow',
                'template_id': template.id,
                'failure_point': execution.current_step
            },
            tags=['workflow', 'failure-pattern', 'sharing', template.id, 'incident', 'prevention']
        )

class AdaptiveWorkflowOptimizer:
    """Optimizes workflows based on collective experience"""
    
    def __init__(self, storage):
        self.storage = storage
        self.optimization_suggestions = defaultdict(list)
    
    async def initialize(self):
        """Initialize adaptive optimizer"""
        pass
    
    async def analyze_for_optimization(self, execution: WorkflowExecution, template: WorkflowTemplate):
        """Analyze execution for optimization opportunities"""
        if execution.status != WorkflowStatus.COMPLETED:
            return
        
        duration = (execution.end_time or time.time()) - execution.start_time
        
        # Analyze step performance
        step_optimizations = []
        for step_id, result in execution.step_results.items():
            step_duration = result.get('duration', 0)
            if step_duration > 60:  # Long-running step
                step_optimizations.append({
                    'type': 'timeout_optimization',
                    'step_id': step_id,
                    'suggestion': f'Consider increasing timeout for step {step_id}',
                    'current_duration': step_duration
                })
        
        # Analyze parameter optimization
        if execution.parameters:
            param_optimizations = await self._analyze_parameter_optimization(execution, template)
            step_optimizations.extend(param_optimizations)
        
        if step_optimizations:
            self.optimization_suggestions[template.id].extend(step_optimizations)
            
            # Store optimization suggestions
            await self.storage.store_memory(
                content=f"Workflow optimization suggestions for {template.name}",
                category="agent",
                context="Workflow optimization analysis",
                metadata={
                    'optimization_suggestions': json.dumps(step_optimizations),
                    'template_id': template.id,
                    'execution_id': execution.id,
                    'analysis_timestamp': time.time()
                },
                tags=['workflow', 'optimization', 'suggestions', template.id, 'haivemind-improvement']
            )
    
    async def analyze_failure_for_improvement(self, execution: WorkflowExecution, template: WorkflowTemplate):
        """Analyze failure for improvement suggestions"""
        improvements = []
        
        if execution.error_message:
            if 'timeout' in execution.error_message.lower():
                improvements.append({
                    'type': 'timeout_improvement',
                    'suggestion': 'Increase timeout values for steps',
                    'priority': 'high'
                })
            
            elif 'connection' in execution.error_message.lower():
                improvements.append({
                    'type': 'retry_improvement',
                    'suggestion': 'Add retry logic for connection failures',
                    'priority': 'medium'
                })
        
        if improvements:
            self.optimization_suggestions[template.id].extend(improvements)
    
    async def _analyze_parameter_optimization(self, execution: WorkflowExecution, 
                                           template: WorkflowTemplate) -> List[Dict[str, Any]]:
        """Analyze parameter optimization opportunities"""
        optimizations = []
        
        # This would analyze parameter effectiveness
        # For now, return empty list
        
        return optimizations
    
    async def get_optimization_suggestions(self, template_id: str) -> List[Dict[str, Any]]:
        """Get optimization suggestions for a workflow"""
        return self.optimization_suggestions.get(template_id, [])

class WorkflowExecutionMonitor:
    """Monitors workflow executions in real-time"""
    
    def __init__(self, storage):
        self.storage = storage
    
    async def monitor_execution(self, execution: WorkflowExecution):
        """Monitor workflow execution progress"""
        # This would provide real-time monitoring
        pass

class WorkflowPerformanceTracker:
    """Tracks workflow performance metrics"""
    
    def __init__(self, storage):
        self.storage = storage
        self.performance_data = defaultdict(dict)
    
    async def get_template_performance(self, template_id: str) -> Dict[str, Any]:
        """Get performance data for a workflow template"""
        try:
            # Search for execution data
            execution_memories = await self.storage.search_memories(
                query=f"workflow execution {template_id}",
                category="agent",
                limit=100
            )
            
            executions = []
            for memory in execution_memories:
                metadata = memory.get('metadata', {})
                if 'workflow_execution_complete' in metadata:
                    exec_data = metadata['workflow_execution_complete']
                    if isinstance(exec_data, str):
                        try:
                            exec_data = json.loads(exec_data)
                        except:
                            continue
                    executions.append(exec_data)
            
            if not executions:
                return {}
            
            # Calculate performance metrics
            total_executions = len(executions)
            successful_executions = sum(1 for e in executions if e.get('success_rate', 0) > 0.8)
            collective_success_rate = successful_executions / total_executions
            
            avg_duration = sum(e.get('duration', 0) for e in executions) / total_executions
            
            # Analyze optimal parameters
            successful_params = [e.get('parameters', {}) for e in executions if e.get('success_rate', 0) > 0.8]
            optimal_parameters = self._analyze_optimal_parameters(successful_params)
            
            # Analyze successful contexts
            successful_contexts = [e.get('trigger_context', {}) for e in executions if e.get('success_rate', 0) > 0.8]
            
            return {
                'collective_success_rate': collective_success_rate,
                'total_executions': total_executions,
                'successful_executions': successful_executions,
                'average_duration': avg_duration,
                'optimal_parameters': optimal_parameters,
                'successful_contexts': successful_contexts[:5]  # Top 5 contexts
            }
        
        except Exception as e:
            logger.error(f"Error getting template performance: {e}")
            return {}
    
    def _analyze_optimal_parameters(self, successful_params: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze optimal parameters from successful executions"""
        if not successful_params:
            return {}
        
        # Find common parameters
        param_counts = defaultdict(Counter)
        
        for params in successful_params:
            for key, value in params.items():
                param_counts[key][str(value)] += 1
        
        # Find most common values for each parameter
        optimal_params = {}
        for param, value_counts in param_counts.items():
            if value_counts:
                most_common_value, count = value_counts.most_common(1)[0]
                if count > len(successful_params) * 0.5:  # Used in >50% of successful executions
                    try:
                        # Try to convert back to original type
                        optimal_params[param] = json.loads(most_common_value)
                    except:
                        optimal_params[param] = most_common_value
        
        return optimal_params

async def create_workflow_haivemind_integration(workflow_engine: WorkflowAutomationEngine, 
                                              storage, config: Dict[str, Any]) -> WorkflowhAIveMindIntegration:
    """Create and initialize workflow hAIveMind integration"""
    integration = WorkflowhAIveMindIntegration(workflow_engine, storage, config)
    await integration.initialize()
    return integration