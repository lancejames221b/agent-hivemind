#!/usr/bin/env python3
"""
Rule Validator - Comprehensive validation and conflict detection for hAIveMind Rules
Provides rule validation, conflict detection, and resolution strategies

Author: Lance James, Unit 221B Inc
"""

import json
import uuid
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from .rules_engine import Rule, RuleType, RuleScope, RulePriority, RuleStatus, ConflictResolution, RuleCondition, RuleAction

class ValidationSeverity(Enum):
    """Validation issue severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

class ConflictType(Enum):
    """Types of rule conflicts"""
    PRIORITY_CONFLICT = "priority_conflict"
    SCOPE_OVERLAP = "scope_overlap"
    ACTION_CONTRADICTION = "action_contradiction"
    CONDITION_CONFLICT = "condition_conflict"
    CIRCULAR_DEPENDENCY = "circular_dependency"
    RESOURCE_CONTENTION = "resource_contention"

@dataclass
class ValidationIssue:
    """Individual validation issue"""
    severity: ValidationSeverity
    message: str
    field: Optional[str] = None
    suggestion: Optional[str] = None
    code: Optional[str] = None

@dataclass
class ValidationResult:
    """Rule validation result"""
    is_valid: bool
    errors: List[ValidationIssue]
    warnings: List[ValidationIssue]
    info: List[ValidationIssue]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "is_valid": self.is_valid,
            "errors": [{"severity": e.severity.value, "message": e.message, "field": e.field, "suggestion": e.suggestion, "code": e.code} for e in self.errors],
            "warnings": [{"severity": w.severity.value, "message": w.message, "field": w.field, "suggestion": w.suggestion, "code": w.code} for w in self.warnings],
            "info": [{"severity": i.severity.value, "message": i.message, "field": i.field, "suggestion": i.suggestion, "code": i.code} for i in self.info]
        }

@dataclass
class RuleConflict:
    """Rule conflict definition"""
    id: str
    conflict_type: ConflictType
    severity: ValidationSeverity
    rule_ids: List[str]
    description: str
    suggested_resolution: str
    metadata: Dict[str, Any]
    detected_at: datetime

class RuleValidator:
    """Comprehensive rule validation and conflict detection"""
    
    def __init__(self, rules_db):
        self.rules_db = rules_db
        self.validation_rules = self._init_validation_rules()
        self.conflict_detectors = self._init_conflict_detectors()
    
    def _init_validation_rules(self) -> Dict[str, callable]:
        """Initialize validation rule functions"""
        return {
            "name_required": self._validate_name_required,
            "name_length": self._validate_name_length,
            "name_uniqueness": self._validate_name_uniqueness,
            "description_required": self._validate_description_required,
            "description_length": self._validate_description_length,
            "conditions_valid": self._validate_conditions,
            "actions_valid": self._validate_actions,
            "actions_required": self._validate_actions_required,
            "priority_valid": self._validate_priority,
            "scope_valid": self._validate_scope,
            "tags_valid": self._validate_tags,
            "circular_dependencies": self._validate_circular_dependencies,
            "effective_dates": self._validate_effective_dates,
            "security_rules": self._validate_security_rules,
            "performance_impact": self._validate_performance_impact
        }
    
    def _init_conflict_detectors(self) -> Dict[ConflictType, callable]:
        """Initialize conflict detection functions"""
        return {
            ConflictType.PRIORITY_CONFLICT: self._detect_priority_conflicts,
            ConflictType.SCOPE_OVERLAP: self._detect_scope_overlaps,
            ConflictType.ACTION_CONTRADICTION: self._detect_action_contradictions,
            ConflictType.CONDITION_CONFLICT: self._detect_condition_conflicts,
            ConflictType.CIRCULAR_DEPENDENCY: self._detect_circular_dependencies,
            ConflictType.RESOURCE_CONTENTION: self._detect_resource_contention
        }
    
    async def validate_rule(self, rule: Rule) -> ValidationResult:
        """Validate a single rule comprehensively"""
        errors = []
        warnings = []
        info = []
        
        # Run all validation rules
        for rule_name, validator_func in self.validation_rules.items():
            try:
                issues = await validator_func(rule)
                for issue in issues:
                    if issue.severity == ValidationSeverity.ERROR:
                        errors.append(issue)
                    elif issue.severity == ValidationSeverity.WARNING:
                        warnings.append(issue)
                    else:
                        info.append(issue)
            except Exception as e:
                errors.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Validation rule '{rule_name}' failed: {str(e)}",
                    code="VALIDATION_ERROR"
                ))
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            info=info
        )
    
    async def detect_rule_conflicts(self, rule: Rule) -> List[RuleConflict]:
        """Detect conflicts for a specific rule against existing rules"""
        conflicts = []
        
        # Get all active rules except the current one
        existing_rules = []
        try:
            # This would need to be implemented in the rules database
            existing_rules = self.rules_db.get_all_active_rules()
            existing_rules = [r for r in existing_rules if r.id != rule.id]
        except:
            pass
        
        # Run conflict detectors
        for conflict_type, detector_func in self.conflict_detectors.items():
            try:
                detected_conflicts = await detector_func(rule, existing_rules)
                conflicts.extend(detected_conflicts)
            except Exception as e:
                # Log error but don't fail the entire detection
                print(f"Conflict detector '{conflict_type.value}' failed: {e}")
        
        return conflicts
    
    async def detect_all_conflicts(self) -> List[RuleConflict]:
        """Detect all conflicts across all rules"""
        all_conflicts = []
        
        try:
            # Get all active rules
            all_rules = self.rules_db.get_all_active_rules()
            
            # Check each rule against all others
            for i, rule in enumerate(all_rules):
                other_rules = all_rules[i+1:]  # Avoid duplicate checks
                
                for conflict_type, detector_func in self.conflict_detectors.items():
                    try:
                        conflicts = await detector_func(rule, other_rules)
                        all_conflicts.extend(conflicts)
                    except Exception as e:
                        print(f"Conflict detector '{conflict_type.value}' failed for rule {rule.id}: {e}")
        
        except Exception as e:
            print(f"Failed to detect all conflicts: {e}")
        
        return all_conflicts
    
    async def resolve_conflict(self, conflict: RuleConflict, resolution_strategy: str, selected_rule_id: str, resolved_by: str) -> Dict[str, Any]:
        """Resolve a rule conflict using the specified strategy"""
        try:
            if resolution_strategy == "disable_conflicting":
                # Disable all conflicting rules except the selected one
                for rule_id in conflict.rule_ids:
                    if rule_id != selected_rule_id:
                        self.rules_db.deactivate_rule(rule_id, resolved_by)
                
                return {
                    "success": True,
                    "action": "disabled_conflicting_rules",
                    "affected_rules": [r for r in conflict.rule_ids if r != selected_rule_id]
                }
            
            elif resolution_strategy == "merge_rules":
                # Attempt to merge conflicting rules
                return await self._merge_conflicting_rules(conflict, resolved_by)
            
            elif resolution_strategy == "prioritize":
                # Update priorities to resolve conflict
                return await self._prioritize_rules(conflict, selected_rule_id, resolved_by)
            
            elif resolution_strategy == "scope_separation":
                # Separate rules by scope to avoid conflict
                return await self._separate_rule_scopes(conflict, resolved_by)
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown resolution strategy: {resolution_strategy}"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    # Validation Rule Functions
    async def _validate_name_required(self, rule: Rule) -> List[ValidationIssue]:
        """Validate that rule name is provided"""
        issues = []
        if not rule.name or not rule.name.strip():
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message="Rule name is required",
                field="name",
                suggestion="Provide a descriptive name for the rule",
                code="NAME_REQUIRED"
            ))
        return issues
    
    async def _validate_name_length(self, rule: Rule) -> List[ValidationIssue]:
        """Validate rule name length"""
        issues = []
        if rule.name and len(rule.name) > 100:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message="Rule name is very long (>100 characters)",
                field="name",
                suggestion="Consider shortening the rule name",
                code="NAME_TOO_LONG"
            ))
        elif rule.name and len(rule.name) < 3:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message="Rule name is very short (<3 characters)",
                field="name",
                suggestion="Consider using a more descriptive name",
                code="NAME_TOO_SHORT"
            ))
        return issues
    
    async def _validate_name_uniqueness(self, rule: Rule) -> List[ValidationIssue]:
        """Validate that rule name is unique"""
        issues = []
        # This would check against existing rules in the database
        # For now, we'll skip this check
        return issues
    
    async def _validate_description_required(self, rule: Rule) -> List[ValidationIssue]:
        """Validate that rule description is provided"""
        issues = []
        if not rule.description or not rule.description.strip():
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message="Rule description is required",
                field="description",
                suggestion="Provide a clear description of what the rule does",
                code="DESCRIPTION_REQUIRED"
            ))
        return issues
    
    async def _validate_description_length(self, rule: Rule) -> List[ValidationIssue]:
        """Validate rule description length"""
        issues = []
        if rule.description and len(rule.description) < 10:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message="Rule description is very short",
                field="description",
                suggestion="Provide a more detailed description",
                code="DESCRIPTION_TOO_SHORT"
            ))
        return issues
    
    async def _validate_conditions(self, rule: Rule) -> List[ValidationIssue]:
        """Validate rule conditions"""
        issues = []
        
        for i, condition in enumerate(rule.conditions):
            if not condition.field:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Condition {i+1}: Field is required",
                    field=f"conditions[{i}].field",
                    code="CONDITION_FIELD_REQUIRED"
                ))
            
            if not condition.operator:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Condition {i+1}: Operator is required",
                    field=f"conditions[{i}].operator",
                    code="CONDITION_OPERATOR_REQUIRED"
                ))
            
            if condition.value is None or condition.value == "":
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Condition {i+1}: Value is required",
                    field=f"conditions[{i}].value",
                    code="CONDITION_VALUE_REQUIRED"
                ))
            
            # Validate regex patterns
            if condition.operator == "regex":
                try:
                    import re
                    re.compile(condition.value)
                except re.error as e:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Condition {i+1}: Invalid regex pattern - {str(e)}",
                        field=f"conditions[{i}].value",
                        suggestion="Provide a valid regular expression",
                        code="INVALID_REGEX"
                    ))
        
        return issues
    
    async def _validate_actions(self, rule: Rule) -> List[ValidationIssue]:
        """Validate rule actions"""
        issues = []
        
        for i, action in enumerate(rule.actions):
            if not action.action_type:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Action {i+1}: Action type is required",
                    field=f"actions[{i}].action_type",
                    code="ACTION_TYPE_REQUIRED"
                ))
            
            if not action.target:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Action {i+1}: Target is required",
                    field=f"actions[{i}].target",
                    code="ACTION_TARGET_REQUIRED"
                ))
            
            if action.value is None:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"Action {i+1}: Value is not set",
                    field=f"actions[{i}].value",
                    code="ACTION_VALUE_EMPTY"
                ))
            
            # Validate action types
            valid_action_types = ["set", "append", "merge", "validate", "block"]
            if action.action_type not in valid_action_types:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Action {i+1}: Invalid action type '{action.action_type}'",
                    field=f"actions[{i}].action_type",
                    suggestion=f"Use one of: {', '.join(valid_action_types)}",
                    code="INVALID_ACTION_TYPE"
                ))
        
        return issues
    
    async def _validate_actions_required(self, rule: Rule) -> List[ValidationIssue]:
        """Validate that at least one action is provided"""
        issues = []
        if not rule.actions or len(rule.actions) == 0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message="At least one action is required",
                field="actions",
                suggestion="Add at least one action to define what the rule does",
                code="ACTIONS_REQUIRED"
            ))
        return issues
    
    async def _validate_priority(self, rule: Rule) -> List[ValidationIssue]:
        """Validate rule priority"""
        issues = []
        priority_value = rule.priority.value if hasattr(rule.priority, 'value') else rule.priority
        
        if priority_value < 1 or priority_value > 1000:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message=f"Priority {priority_value} is outside recommended range (1-1000)",
                field="priority",
                suggestion="Use priority values between 1 and 1000",
                code="PRIORITY_OUT_OF_RANGE"
            ))
        
        return issues
    
    async def _validate_scope(self, rule: Rule) -> List[ValidationIssue]:
        """Validate rule scope"""
        issues = []
        # Scope validation is handled by enum, so no additional validation needed
        return issues
    
    async def _validate_tags(self, rule: Rule) -> List[ValidationIssue]:
        """Validate rule tags"""
        issues = []
        
        if rule.tags:
            for i, tag in enumerate(rule.tags):
                if not tag or not tag.strip():
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        message=f"Tag {i+1} is empty",
                        field=f"tags[{i}]",
                        code="EMPTY_TAG"
                    ))
                elif len(tag) > 50:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        message=f"Tag '{tag}' is very long (>50 characters)",
                        field=f"tags[{i}]",
                        suggestion="Use shorter, more concise tags",
                        code="TAG_TOO_LONG"
                    ))
        
        return issues
    
    async def _validate_circular_dependencies(self, rule: Rule) -> List[ValidationIssue]:
        """Validate that rule doesn't create circular dependencies"""
        issues = []
        # This would require checking the dependency graph
        # For now, we'll skip this complex validation
        return issues
    
    async def _validate_effective_dates(self, rule: Rule) -> List[ValidationIssue]:
        """Validate effective dates"""
        issues = []
        
        if hasattr(rule, 'effective_from') and hasattr(rule, 'effective_until'):
            if rule.effective_from and rule.effective_until:
                if rule.effective_from >= rule.effective_until:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message="Effective from date must be before effective until date",
                        field="effective_dates",
                        code="INVALID_DATE_RANGE"
                    ))
        
        return issues
    
    async def _validate_security_rules(self, rule: Rule) -> List[ValidationIssue]:
        """Validate security-specific rules"""
        issues = []
        
        if rule.rule_type == RuleType.SECURITY:
            # Security rules should have high priority
            priority_value = rule.priority.value if hasattr(rule.priority, 'value') else rule.priority
            if priority_value < 750:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message="Security rules should have high priority (≥750)",
                    field="priority",
                    suggestion="Consider increasing priority for security rules",
                    code="SECURITY_LOW_PRIORITY"
                ))
            
            # Security rules should be global or project scope
            if rule.scope not in [RuleScope.GLOBAL, RuleScope.PROJECT]:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message="Security rules are typically global or project-scoped",
                    field="scope",
                    suggestion="Consider using global or project scope for security rules",
                    code="SECURITY_NARROW_SCOPE"
                ))
        
        return issues
    
    async def _validate_performance_impact(self, rule: Rule) -> List[ValidationIssue]:
        """Validate potential performance impact"""
        issues = []
        
        # Check for complex regex patterns
        for condition in rule.conditions:
            if condition.operator == "regex" and len(str(condition.value)) > 100:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message="Complex regex patterns may impact performance",
                    field="conditions",
                    suggestion="Consider simplifying regex patterns or using alternative operators",
                    code="COMPLEX_REGEX"
                ))
        
        # Check for too many conditions
        if len(rule.conditions) > 10:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message=f"Rule has many conditions ({len(rule.conditions)}), may impact performance",
                field="conditions",
                suggestion="Consider breaking complex rules into simpler ones",
                code="TOO_MANY_CONDITIONS"
            ))
        
        return issues
    
    # Conflict Detection Functions
    async def _detect_priority_conflicts(self, rule: Rule, other_rules: List[Rule]) -> List[RuleConflict]:
        """Detect priority-based conflicts"""
        conflicts = []
        
        # Find rules with same priority targeting same scope
        rule_priority = rule.priority.value if hasattr(rule.priority, 'value') else rule.priority
        
        for other_rule in other_rules:
            other_priority = other_rule.priority.value if hasattr(other_rule.priority, 'value') else other_rule.priority
            
            if (rule_priority == other_priority and 
                rule.scope == other_rule.scope and
                self._rules_have_overlapping_targets(rule, other_rule)):
                
                conflicts.append(RuleConflict(
                    id=str(uuid.uuid4()),
                    conflict_type=ConflictType.PRIORITY_CONFLICT,
                    severity=ValidationSeverity.WARNING,
                    rule_ids=[rule.id, other_rule.id],
                    description=f"Rules '{rule.name}' and '{other_rule.name}' have same priority ({rule_priority}) and overlapping targets",
                    suggested_resolution="Adjust priorities or separate scopes",
                    metadata={
                        "priority": rule_priority,
                        "scope": rule.scope.value,
                        "overlapping_targets": self._get_overlapping_targets(rule, other_rule)
                    },
                    detected_at=datetime.now()
                ))
        
        return conflicts
    
    async def _detect_scope_overlaps(self, rule: Rule, other_rules: List[Rule]) -> List[RuleConflict]:
        """Detect scope overlap conflicts"""
        conflicts = []
        
        for other_rule in other_rules:
            if (rule.scope == other_rule.scope and
                rule.rule_type == other_rule.rule_type and
                self._rules_have_conflicting_actions(rule, other_rule)):
                
                conflicts.append(RuleConflict(
                    id=str(uuid.uuid4()),
                    conflict_type=ConflictType.SCOPE_OVERLAP,
                    severity=ValidationSeverity.ERROR,
                    rule_ids=[rule.id, other_rule.id],
                    description=f"Rules '{rule.name}' and '{other_rule.name}' have overlapping scope with conflicting actions",
                    suggested_resolution="Separate scopes or merge rules",
                    metadata={
                        "scope": rule.scope.value,
                        "rule_type": rule.rule_type.value,
                        "conflicting_actions": self._get_conflicting_actions(rule, other_rule)
                    },
                    detected_at=datetime.now()
                ))
        
        return conflicts
    
    async def _detect_action_contradictions(self, rule: Rule, other_rules: List[Rule]) -> List[RuleConflict]:
        """Detect contradictory actions"""
        conflicts = []
        
        for other_rule in other_rules:
            contradictions = self._find_action_contradictions(rule, other_rule)
            if contradictions:
                conflicts.append(RuleConflict(
                    id=str(uuid.uuid4()),
                    conflict_type=ConflictType.ACTION_CONTRADICTION,
                    severity=ValidationSeverity.ERROR,
                    rule_ids=[rule.id, other_rule.id],
                    description=f"Rules '{rule.name}' and '{other_rule.name}' have contradictory actions",
                    suggested_resolution="Resolve contradictions or adjust priorities",
                    metadata={
                        "contradictions": contradictions
                    },
                    detected_at=datetime.now()
                ))
        
        return conflicts
    
    async def _detect_condition_conflicts(self, rule: Rule, other_rules: List[Rule]) -> List[RuleConflict]:
        """Detect conflicting conditions"""
        conflicts = []
        # Implementation would check for mutually exclusive conditions
        return conflicts
    
    async def _detect_circular_dependencies(self, rule: Rule, other_rules: List[Rule]) -> List[RuleConflict]:
        """Detect circular dependencies"""
        conflicts = []
        # Implementation would check dependency graph for cycles
        return conflicts
    
    async def _detect_resource_contention(self, rule: Rule, other_rules: List[Rule]) -> List[RuleConflict]:
        """Detect resource contention conflicts"""
        conflicts = []
        # Implementation would check for rules competing for same resources
        return conflicts
    
    # Helper Methods
    def _rules_have_overlapping_targets(self, rule1: Rule, rule2: Rule) -> bool:
        """Check if two rules have overlapping action targets"""
        targets1 = {action.target for action in rule1.actions}
        targets2 = {action.target for action in rule2.actions}
        return bool(targets1.intersection(targets2))
    
    def _get_overlapping_targets(self, rule1: Rule, rule2: Rule) -> List[str]:
        """Get list of overlapping action targets"""
        targets1 = {action.target for action in rule1.actions}
        targets2 = {action.target for action in rule2.actions}
        return list(targets1.intersection(targets2))
    
    def _rules_have_conflicting_actions(self, rule1: Rule, rule2: Rule) -> bool:
        """Check if two rules have conflicting actions"""
        return len(self._find_action_contradictions(rule1, rule2)) > 0
    
    def _get_conflicting_actions(self, rule1: Rule, rule2: Rule) -> List[Dict[str, Any]]:
        """Get list of conflicting actions between two rules"""
        return self._find_action_contradictions(rule1, rule2)
    
    def _find_action_contradictions(self, rule1: Rule, rule2: Rule) -> List[Dict[str, Any]]:
        """Find contradictory actions between two rules"""
        contradictions = []
        
        for action1 in rule1.actions:
            for action2 in rule2.actions:
                if (action1.target == action2.target and
                    self._actions_contradict(action1, action2)):
                    
                    contradictions.append({
                        "target": action1.target,
                        "rule1_action": {
                            "type": action1.action_type,
                            "value": action1.value
                        },
                        "rule2_action": {
                            "type": action2.action_type,
                            "value": action2.value
                        }
                    })
        
        return contradictions
    
    def _actions_contradict(self, action1: RuleAction, action2: RuleAction) -> bool:
        """Check if two actions contradict each other"""
        # Set actions with different values contradict
        if (action1.action_type == "set" and action2.action_type == "set" and
            action1.value != action2.value):
            return True
        
        # Block action contradicts any other action on same target
        if (action1.action_type == "block" or action2.action_type == "block"):
            return True
        
        # Add more contradiction logic as needed
        return False
    
    # Resolution Helper Methods
    async def _merge_conflicting_rules(self, conflict: RuleConflict, resolved_by: str) -> Dict[str, Any]:
        """Attempt to merge conflicting rules"""
        # This would implement rule merging logic
        return {"success": False, "error": "Rule merging not implemented"}
    
    async def _prioritize_rules(self, conflict: RuleConflict, selected_rule_id: str, resolved_by: str) -> Dict[str, Any]:
        """Resolve conflict by adjusting priorities"""
        # This would implement priority adjustment logic
        return {"success": False, "error": "Priority adjustment not implemented"}
    
    async def _separate_rule_scopes(self, conflict: RuleConflict, resolved_by: str) -> Dict[str, Any]:
        """Resolve conflict by separating rule scopes"""
        # This would implement scope separation logic
        return {"success": False, "error": "Scope separation not implemented"}