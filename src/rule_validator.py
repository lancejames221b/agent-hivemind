#!/usr/bin/env python3
"""
hAIveMind Rule Validation and Syntax Checking System
Validates rule definitions, syntax, and logical consistency

Author: Lance James, Unit 221B Inc
"""

import re
import json
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime

from .rules_engine import Rule, RuleCondition, RuleAction, RuleType, RuleScope, RulePriority, RuleStatus

logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    """Validation severity levels"""
    ERROR = "error"         # Rule cannot be applied
    WARNING = "warning"     # Rule may not work as expected
    INFO = "info"          # Suggestions for improvement
    
class ValidationCategory(Enum):
    """Categories of validation checks"""
    SYNTAX = "syntax"
    LOGIC = "logic"
    PERFORMANCE = "performance" 
    SECURITY = "security"
    COMPATIBILITY = "compatibility"
    STYLE = "style"

@dataclass
class ValidationResult:
    """Result of rule validation"""
    level: ValidationLevel
    category: ValidationCategory
    message: str
    field: Optional[str] = None
    suggestion: Optional[str] = None
    auto_fix_available: bool = False

class RuleValidator:
    """Comprehensive rule validation and syntax checking"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.known_fields = self._get_known_context_fields()
        self.supported_operators = {
            'eq', 'ne', 'in', 'regex', 'contains', 'startswith', 'endswith',
            'gt', 'lt', 'gte', 'lte', 'exists', 'not_exists'
        }
        self.supported_actions = {
            'set', 'append', 'merge', 'validate', 'block', 'transform', 'invoke'
        }
    
    def validate_rule(self, rule: Rule) -> List[ValidationResult]:
        """Comprehensive rule validation"""
        results = []
        
        # Basic syntax validation
        results.extend(self._validate_basic_syntax(rule))
        
        # Condition validation
        results.extend(self._validate_conditions(rule))
        
        # Action validation
        results.extend(self._validate_actions(rule))
        
        # Logic validation
        results.extend(self._validate_logic(rule))
        
        # Performance validation
        results.extend(self._validate_performance(rule))
        
        # Security validation
        results.extend(self._validate_security(rule))
        
        # Compatibility validation
        results.extend(self._validate_compatibility(rule))
        
        return results
    
    def _validate_basic_syntax(self, rule: Rule) -> List[ValidationResult]:
        """Validate basic rule syntax and structure"""
        results = []
        
        # Required fields
        if not rule.id:
            results.append(ValidationResult(
                ValidationLevel.ERROR, 
                ValidationCategory.SYNTAX,
                "Rule ID is required",
                field="id",
                auto_fix_available=True
            ))
        
        if not rule.name or not rule.name.strip():
            results.append(ValidationResult(
                ValidationLevel.ERROR,
                ValidationCategory.SYNTAX,
                "Rule name is required and cannot be empty",
                field="name"
            ))
        
        if not rule.description or not rule.description.strip():
            results.append(ValidationResult(
                ValidationLevel.WARNING,
                ValidationCategory.STYLE,
                "Rule description is empty - add description for maintainability",
                field="description"
            ))
        
        # ID format validation
        if rule.id and not re.match(r'^[a-zA-Z0-9_-]+$', rule.id):
            results.append(ValidationResult(
                ValidationLevel.ERROR,
                ValidationCategory.SYNTAX,
                "Rule ID must contain only alphanumeric characters, underscores, and hyphens",
                field="id"
            ))
        
        # Name format validation
        if rule.name and len(rule.name) > 100:
            results.append(ValidationResult(
                ValidationLevel.WARNING,
                ValidationCategory.STYLE,
                "Rule name is very long (>100 chars) - consider shortening",
                field="name"
            ))
        
        # Description length
        if rule.description and len(rule.description) > 500:
            results.append(ValidationResult(
                ValidationLevel.INFO,
                ValidationCategory.STYLE,
                "Rule description is very long (>500 chars) - consider shortening",
                field="description"
            ))
        
        # Tags validation
        if rule.tags:
            for tag in rule.tags:
                if not re.match(r'^[a-zA-Z0-9_-]+$', tag):
                    results.append(ValidationResult(
                        ValidationLevel.WARNING,
                        ValidationCategory.SYNTAX,
                        f"Tag '{tag}' contains invalid characters",
                        field="tags"
                    ))
        
        return results
    
    def _validate_conditions(self, rule: Rule) -> List[ValidationResult]:
        """Validate rule conditions"""
        results = []
        
        if not rule.conditions:
            results.append(ValidationResult(
                ValidationLevel.INFO,
                ValidationCategory.LOGIC,
                "Rule has no conditions - will apply to all contexts",
                field="conditions"
            ))
            return results
        
        for i, condition in enumerate(rule.conditions):
            field_prefix = f"conditions[{i}]"
            
            # Required fields
            if not condition.field:
                results.append(ValidationResult(
                    ValidationLevel.ERROR,
                    ValidationCategory.SYNTAX,
                    "Condition field is required",
                    field=f"{field_prefix}.field"
                ))
            
            if not condition.operator:
                results.append(ValidationResult(
                    ValidationLevel.ERROR,
                    ValidationCategory.SYNTAX,
                    "Condition operator is required",
                    field=f"{field_prefix}.operator"
                ))
            
            # Operator validation
            if condition.operator and condition.operator not in self.supported_operators:
                results.append(ValidationResult(
                    ValidationLevel.ERROR,
                    ValidationCategory.SYNTAX,
                    f"Unsupported operator '{condition.operator}'. Supported: {', '.join(self.supported_operators)}",
                    field=f"{field_prefix}.operator"
                ))
            
            # Field name validation
            if condition.field and condition.field not in self.known_fields:
                results.append(ValidationResult(
                    ValidationLevel.WARNING,
                    ValidationCategory.COMPATIBILITY,
                    f"Unknown context field '{condition.field}' - ensure this field exists in evaluation context",
                    field=f"{field_prefix}.field",
                    suggestion=f"Known fields: {', '.join(sorted(self.known_fields))}"
                ))
            
            # Value validation based on operator
            if condition.operator == 'regex':
                try:
                    re.compile(condition.value)
                except re.error as e:
                    results.append(ValidationResult(
                        ValidationLevel.ERROR,
                        ValidationCategory.SYNTAX,
                        f"Invalid regex pattern: {e}",
                        field=f"{field_prefix}.value"
                    ))
            
            if condition.operator == 'in' and not isinstance(condition.value, list):
                results.append(ValidationResult(
                    ValidationLevel.ERROR,
                    ValidationCategory.SYNTAX,
                    "Operator 'in' requires value to be a list",
                    field=f"{field_prefix}.value"
                ))
            
            # Performance warnings
            if condition.operator == 'regex' and len(str(condition.value)) > 100:
                results.append(ValidationResult(
                    ValidationLevel.WARNING,
                    ValidationCategory.PERFORMANCE,
                    "Complex regex patterns may impact performance",
                    field=f"{field_prefix}.value"
                ))
        
        # Check for contradictory conditions
        field_conditions = {}
        for condition in rule.conditions:
            if condition.field not in field_conditions:
                field_conditions[condition.field] = []
            field_conditions[condition.field].append(condition)
        
        for field, conditions in field_conditions.items():
            if len(conditions) > 1:
                # Check for contradictions
                eq_values = [c.value for c in conditions if c.operator == 'eq']
                if len(eq_values) > 1 and len(set(eq_values)) > 1:
                    results.append(ValidationResult(
                        ValidationLevel.ERROR,
                        ValidationCategory.LOGIC,
                        f"Contradictory conditions on field '{field}' - multiple different equality checks",
                        field="conditions"
                    ))
        
        return results
    
    def _validate_actions(self, rule: Rule) -> List[ValidationResult]:
        """Validate rule actions"""
        results = []
        
        if not rule.actions:
            results.append(ValidationResult(
                ValidationLevel.ERROR,
                ValidationCategory.LOGIC,
                "Rule must have at least one action",
                field="actions"
            ))
            return results
        
        target_counts = {}
        
        for i, action in enumerate(rule.actions):
            field_prefix = f"actions[{i}]"
            
            # Required fields
            if not action.action_type:
                results.append(ValidationResult(
                    ValidationLevel.ERROR,
                    ValidationCategory.SYNTAX,
                    "Action type is required",
                    field=f"{field_prefix}.action_type"
                ))
            
            if not action.target:
                results.append(ValidationResult(
                    ValidationLevel.ERROR,
                    ValidationCategory.SYNTAX,
                    "Action target is required",
                    field=f"{field_prefix}.target"
                ))
            
            # Action type validation
            if action.action_type and action.action_type not in self.supported_actions:
                results.append(ValidationResult(
                    ValidationLevel.ERROR,
                    ValidationCategory.SYNTAX,
                    f"Unsupported action type '{action.action_type}'. Supported: {', '.join(self.supported_actions)}",
                    field=f"{field_prefix}.action_type"
                ))
            
            # Value validation based on action type
            if action.action_type == 'append' and not isinstance(action.value, (list, str)):
                results.append(ValidationResult(
                    ValidationLevel.WARNING,
                    ValidationCategory.LOGIC,
                    "Append action typically expects list or string value",
                    field=f"{field_prefix}.value"
                ))
            
            if action.action_type == 'merge' and not isinstance(action.value, dict):
                results.append(ValidationResult(
                    ValidationLevel.ERROR,
                    ValidationCategory.SYNTAX,
                    "Merge action requires dict value",
                    field=f"{field_prefix}.value"
                ))
            
            # Track target usage
            target_counts[action.target] = target_counts.get(action.target, 0) + 1
        
        # Check for duplicate targets
        for target, count in target_counts.items():
            if count > 1:
                results.append(ValidationResult(
                    ValidationLevel.WARNING,
                    ValidationCategory.LOGIC,
                    f"Multiple actions target '{target}' - only last action will be effective",
                    field="actions",
                    suggestion="Consider using single action or different conflict resolution"
                ))
        
        return results
    
    def _validate_logic(self, rule: Rule) -> List[ValidationResult]:
        """Validate rule logic consistency"""
        results = []
        
        # Check scope vs conditions consistency
        scope_field_mapping = {
            RuleScope.PROJECT: 'project_id',
            RuleScope.MACHINE: 'machine_id', 
            RuleScope.AGENT: 'agent_id',
            RuleScope.SESSION: 'session_id'
        }
        
        expected_field = scope_field_mapping.get(rule.scope)
        if expected_field:
            has_scope_condition = any(c.field == expected_field for c in rule.conditions)
            if not has_scope_condition:
                results.append(ValidationResult(
                    ValidationLevel.WARNING,
                    ValidationCategory.LOGIC,
                    f"Rule has scope '{rule.scope.value}' but no condition on '{expected_field}' - may apply too broadly",
                    field="conditions",
                    suggestion=f"Add condition: {expected_field} = <specific_value>"
                ))
        
        # Check priority vs scope consistency
        if rule.scope == RuleScope.GLOBAL and rule.priority == RulePriority.LOW:
            results.append(ValidationResult(
                ValidationLevel.INFO,
                ValidationCategory.LOGIC,
                "Global scope with low priority may be frequently overridden",
                field="priority"
            ))
        
        if rule.scope in [RuleScope.AGENT, RuleScope.SESSION] and rule.priority == RulePriority.CRITICAL:
            results.append(ValidationResult(
                ValidationLevel.INFO,
                ValidationCategory.LOGIC,
                "Specific scope with critical priority may be overly restrictive",
                field="priority"
            ))
        
        return results
    
    def _validate_performance(self, rule: Rule) -> List[ValidationResult]:
        """Validate rule performance characteristics"""
        results = []
        
        # Complex condition patterns
        regex_conditions = [c for c in rule.conditions if c.operator == 'regex']
        if len(regex_conditions) > 3:
            results.append(ValidationResult(
                ValidationLevel.WARNING,
                ValidationCategory.PERFORMANCE,
                f"Rule has {len(regex_conditions)} regex conditions - may impact evaluation performance",
                field="conditions",
                suggestion="Consider simplifying conditions or using caching"
            ))
        
        # Large value lists
        for condition in rule.conditions:
            if condition.operator == 'in' and isinstance(condition.value, list) and len(condition.value) > 20:
                results.append(ValidationResult(
                    ValidationLevel.WARNING,
                    ValidationCategory.PERFORMANCE,
                    f"Large value list ({len(condition.value)} items) in 'in' operator may impact performance",
                    field="conditions"
                ))
        
        # Action complexity
        complex_actions = [a for a in rule.actions if a.action_type in ['transform', 'invoke']]
        if len(complex_actions) > 2:
            results.append(ValidationResult(
                ValidationLevel.INFO,
                ValidationCategory.PERFORMANCE,
                "Multiple complex actions may impact rule evaluation speed",
                field="actions"
            ))
        
        return results
    
    def _validate_security(self, rule: Rule) -> List[ValidationResult]:
        """Validate rule security implications"""
        results = []
        
        # Check for security-sensitive actions
        security_sensitive_targets = [
            'password', 'secret', 'key', 'token', 'credential', 'auth'
        ]
        
        for action in rule.actions:
            if any(sensitive in action.target.lower() for sensitive in security_sensitive_targets):
                if action.action_type == 'set' and isinstance(action.value, str) and len(action.value) > 10:
                    results.append(ValidationResult(
                        ValidationLevel.WARNING,
                        ValidationCategory.SECURITY,
                        f"Action sets potentially sensitive target '{action.target}' with literal value",
                        field="actions",
                        suggestion="Consider using secure parameter or environment variable"
                    ))
        
        # Check for overly broad conditions
        if not rule.conditions or len(rule.conditions) == 0:
            if rule.rule_type in [RuleType.SECURITY, RuleType.COMPLIANCE]:
                results.append(ValidationResult(
                    ValidationLevel.WARNING,
                    ValidationCategory.SECURITY,
                    "Security/compliance rule has no conditions - applies to all contexts",
                    field="conditions",
                    suggestion="Add specific conditions to limit rule scope"
                ))
        
        # Validate regex patterns for injection risks
        for condition in rule.conditions:
            if condition.operator == 'regex' and isinstance(condition.value, str):
                # Check for potentially unsafe regex patterns
                if '.*' in condition.value and len(condition.value.replace('.*', '')) < 5:
                    results.append(ValidationResult(
                        ValidationLevel.WARNING,
                        ValidationCategory.SECURITY,
                        "Regex pattern is very broad and may match unintended content",
                        field="conditions"
                    ))
        
        return results
    
    def _validate_compatibility(self, rule: Rule) -> List[ValidationResult]:
        """Validate rule compatibility with system"""
        results = []
        
        # Check for deprecated features
        deprecated_operators = {'like', 'ilike'}  # Example deprecated operators
        for condition in rule.conditions:
            if condition.operator in deprecated_operators:
                results.append(ValidationResult(
                    ValidationLevel.WARNING,
                    ValidationCategory.COMPATIBILITY,
                    f"Operator '{condition.operator}' is deprecated - use 'contains' or 'regex' instead",
                    field="conditions",
                    auto_fix_available=True
                ))
        
        # Version compatibility checks
        if rule.version and rule.version < 1:
            results.append(ValidationResult(
                ValidationLevel.ERROR,
                ValidationCategory.COMPATIBILITY,
                "Rule version must be >= 1",
                field="version",
                auto_fix_available=True
            ))
        
        return results
    
    def auto_fix_rule(self, rule: Rule, validation_results: List[ValidationResult]) -> Tuple[Rule, List[str]]:
        """Apply automatic fixes for validation issues where possible"""
        fixed_rule = rule
        applied_fixes = []
        
        for result in validation_results:
            if not result.auto_fix_available:
                continue
                
            if result.field == "id" and not rule.id:
                # Generate ID from name
                import uuid
                fixed_rule.id = f"rule_{re.sub(r'[^a-zA-Z0-9]', '_', rule.name.lower())}_{str(uuid.uuid4())[:8]}"
                applied_fixes.append("Generated missing rule ID")
            
            elif result.field == "version" and rule.version < 1:
                fixed_rule.version = 1
                applied_fixes.append("Set version to 1")
            
            elif "deprecated operator" in result.message:
                # Fix deprecated operators
                for condition in fixed_rule.conditions:
                    if condition.operator == 'like':
                        condition.operator = 'contains'
                        applied_fixes.append("Replaced 'like' with 'contains'")
                    elif condition.operator == 'ilike':
                        condition.operator = 'contains'
                        condition.case_sensitive = False
                        applied_fixes.append("Replaced 'ilike' with case-insensitive 'contains'")
        
        return fixed_rule, applied_fixes
    
    def _get_known_context_fields(self) -> set:
        """Get known context fields that rules can reference"""
        return {
            'agent_id', 'machine_id', 'project_id', 'session_id', 'user_id',
            'capabilities', 'role', 'hostname', 'os', 'platform', 'user',
            'working_directory', 'git_branch', 'git_repo', 'file_type',
            'task_type', 'conversation_length', 'time_of_day', 'day_of_week'
        }
    
    def validate_rule_set(self, rules: List[Rule]) -> Dict[str, Any]:
        """Validate a set of rules for conflicts and consistency"""
        
        all_results = []
        rule_conflicts = []
        
        # Validate each rule individually
        for rule in rules:
            results = self.validate_rule(rule)
            all_results.extend([(rule.id, result) for result in results])
        
        # Check for conflicts between rules
        rule_conflicts.extend(self._find_rule_conflicts(rules))
        
        # Summary statistics
        error_count = sum(1 for _, result in all_results if result.level == ValidationLevel.ERROR)
        warning_count = sum(1 for _, result in all_results if result.level == ValidationLevel.WARNING)
        
        return {
            'valid': error_count == 0,
            'total_rules': len(rules),
            'error_count': error_count,
            'warning_count': warning_count,
            'rule_results': all_results,
            'rule_conflicts': rule_conflicts,
            'summary': f"Validated {len(rules)} rules: {error_count} errors, {warning_count} warnings"
        }
    
    def _find_rule_conflicts(self, rules: List[Rule]) -> List[Dict[str, Any]]:
        """Find potential conflicts between rules"""
        conflicts = []
        
        # Group rules by target
        target_rules = {}
        for rule in rules:
            for action in rule.actions:
                if action.target not in target_rules:
                    target_rules[action.target] = []
                target_rules[action.target].append((rule, action))
        
        # Check for conflicts within each target group
        for target, rule_actions in target_rules.items():
            if len(rule_actions) < 2:
                continue
                
            # Check for same priority conflicts
            priority_groups = {}
            for rule, action in rule_actions:
                priority = rule.priority.value
                if priority not in priority_groups:
                    priority_groups[priority] = []
                priority_groups[priority].append((rule, action))
            
            for priority, group in priority_groups.items():
                if len(group) > 1:
                    # Check if rules have overlapping conditions
                    overlapping_rules = self._find_overlapping_rules([r for r, a in group])
                    if overlapping_rules:
                        conflicts.append({
                            'type': 'priority_conflict',
                            'target': target,
                            'priority': priority,
                            'conflicting_rules': [r.id for r in overlapping_rules],
                            'message': f"Multiple rules with same priority target '{target}'"
                        })
        
        return conflicts
    
    def _find_overlapping_rules(self, rules: List[Rule]) -> List[Rule]:
        """Find rules with potentially overlapping conditions"""
        # Simplified overlap detection - could be more sophisticated
        overlapping = []
        
        for i, rule1 in enumerate(rules):
            for rule2 in rules[i+1:]:
                if self._rules_may_overlap(rule1, rule2):
                    overlapping.extend([rule1, rule2])
        
        return list(set(overlapping))
    
    def _rules_may_overlap(self, rule1: Rule, rule2: Rule) -> bool:
        """Check if two rules may have overlapping conditions"""
        
        # If either has no conditions, they potentially overlap
        if not rule1.conditions or not rule2.conditions:
            return True
        
        # Check for common fields with compatible values
        rule1_fields = {c.field: c for c in rule1.conditions}
        rule2_fields = {c.field: c for c in rule2.conditions}
        
        common_fields = set(rule1_fields.keys()) & set(rule2_fields.keys())
        
        for field in common_fields:
            c1, c2 = rule1_fields[field], rule2_fields[field]
            
            # Simple overlap check for equality conditions
            if c1.operator == 'eq' and c2.operator == 'eq':
                if c1.value != c2.value:
                    return False  # Mutually exclusive
            
        return True  # Assume overlap if we can't prove otherwise