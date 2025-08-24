#!/usr/bin/env python3
"""
hAIveMind Rule Inheritance System
Manages rule hierarchies, inheritance patterns, and override mechanisms

Author: Lance James, Unit 221B Inc
"""

from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, replace
import json
import logging
from datetime import datetime

from .rules_engine import Rule, RuleScope, RulePriority, RuleType, ConflictResolution

logger = logging.getLogger(__name__)

@dataclass
class InheritanceContext:
    """Context for rule inheritance evaluation"""
    agent_id: str
    machine_id: str
    project_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    capabilities: List[str] = None
    role: Optional[str] = None

class RuleInheritanceManager:
    """Manages rule inheritance hierarchies and override mechanisms"""
    
    def __init__(self, rules_db):
        self.rules_db = rules_db
        self.inheritance_cache = {}
        
    def get_effective_rules(self, context: InheritanceContext) -> List[Rule]:
        """Get effective rules for context, applying inheritance and overrides"""
        
        # Build inheritance hierarchy
        hierarchy = self._build_inheritance_hierarchy(context)
        
        # Collect rules from all levels
        all_rules = {}  # rule_id -> (rule, scope_level)
        scope_priorities = {
            RuleScope.GLOBAL: 1,
            RuleScope.PROJECT: 2, 
            RuleScope.MACHINE: 3,
            RuleScope.AGENT: 4,
            RuleScope.SESSION: 5
        }
        
        for scope, rules in hierarchy.items():
            scope_level = scope_priorities.get(scope, 0)
            for rule in rules:
                existing = all_rules.get(rule.id)
                if not existing or existing[1] < scope_level:
                    all_rules[rule.id] = (rule, scope_level)
        
        # Apply inheritance and overrides
        effective_rules = []
        processed_types = {}  # track rule types to handle inheritance
        
        # Sort by scope priority (most specific first) then by rule priority
        sorted_rules = sorted(all_rules.values(), 
                            key=lambda x: (x[1], x[0].priority.value), 
                            reverse=True)
        
        for rule, scope_level in sorted_rules:
            # Check for inheritance relationships
            if rule.parent_rule_id:
                parent_rule = self._get_parent_rule(rule.parent_rule_id)
                if parent_rule:
                    # Create inherited rule by merging parent and child
                    inherited_rule = self._merge_inherited_rule(parent_rule, rule)
                    effective_rules.append(inherited_rule)
                else:
                    effective_rules.append(rule)
            else:
                # Check if this rule type has been overridden by a more specific scope
                rule_type_key = f"{rule.rule_type.value}:{rule.name}"
                if rule_type_key not in processed_types or processed_types[rule_type_key][1] <= scope_level:
                    processed_types[rule_type_key] = (rule, scope_level)
                    effective_rules.append(rule)
        
        # Remove duplicates and sort by final priority
        unique_rules = {r.id: r for r in effective_rules}
        final_rules = sorted(unique_rules.values(), 
                           key=lambda x: x.priority.value, 
                           reverse=True)
        
        return final_rules
    
    def _build_inheritance_hierarchy(self, context: InheritanceContext) -> Dict[RuleScope, List[Rule]]:
        """Build rule inheritance hierarchy for given context"""
        hierarchy = {}
        
        # Global rules (base layer)
        hierarchy[RuleScope.GLOBAL] = self._get_rules_by_scope(RuleScope.GLOBAL)
        
        # Project-specific rules
        if context.project_id:
            project_rules = self._get_rules_by_scope(RuleScope.PROJECT, 
                                                   {"project_id": context.project_id})
            hierarchy[RuleScope.PROJECT] = project_rules
        
        # Machine-specific rules  
        machine_rules = self._get_rules_by_scope(RuleScope.MACHINE,
                                                {"machine_id": context.machine_id})
        hierarchy[RuleScope.MACHINE] = machine_rules
        
        # Agent-specific rules
        agent_rules = self._get_rules_by_scope(RuleScope.AGENT,
                                             {"agent_id": context.agent_id})
        hierarchy[RuleScope.AGENT] = agent_rules
        
        # Session-specific rules
        if context.session_id:
            session_rules = self._get_rules_by_scope(RuleScope.SESSION,
                                                   {"session_id": context.session_id})
            hierarchy[RuleScope.SESSION] = session_rules
        
        return hierarchy
    
    def _get_rules_by_scope(self, scope: RuleScope, filters: Dict[str, Any] = None) -> List[Rule]:
        """Get rules for specific scope with optional filters"""
        import sqlite3
        
        query = "SELECT * FROM rules WHERE scope = ? AND status = 'active'"
        params = [scope.value]
        
        # Add filter conditions
        if filters:
            for key, value in filters.items():
                # Check if rule conditions match filter
                query += f" AND JSON_EXTRACT(conditions, '$[*].field') LIKE '%{key}%'"
        
        with sqlite3.connect(self.rules_db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            
            rules = []
            for row in cursor.fetchall():
                rule = self.rules_db._row_to_rule(row)
                # Additional filtering based on conditions
                if filters and not self._rule_matches_filters(rule, filters):
                    continue
                rules.append(rule)
                
            return rules
    
    def _rule_matches_filters(self, rule: Rule, filters: Dict[str, Any]) -> bool:
        """Check if rule conditions match the given filters"""
        if not rule.conditions:
            return True  # Rules without conditions apply to all contexts
            
        for condition in rule.conditions:
            filter_value = filters.get(condition.field)
            if filter_value is None:
                continue
                
            # Use the existing condition evaluation logic
            if not self.rules_db._evaluate_condition(condition, filters):
                return False
                
        return True
    
    def _get_parent_rule(self, parent_rule_id: str) -> Optional[Rule]:
        """Get parent rule by ID"""
        import sqlite3
        
        with sqlite3.connect(self.rules_db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM rules WHERE id = ?", (parent_rule_id,))
            row = cursor.fetchone()
            if row:
                return self.rules_db._row_to_rule(row)
        return None
    
    def _merge_inherited_rule(self, parent: Rule, child: Rule) -> Rule:
        """Merge parent and child rules to create effective inherited rule"""
        
        # Child rule takes precedence for most fields
        merged_rule = replace(child)
        
        # Merge conditions (child conditions AND parent conditions)
        merged_conditions = list(parent.conditions)
        for child_condition in child.conditions:
            # Avoid duplicate conditions
            if not any(c.field == child_condition.field and c.operator == child_condition.operator 
                      for c in merged_conditions):
                merged_conditions.append(child_condition)
        merged_rule.conditions = merged_conditions
        
        # Merge actions (child actions override parent for same targets)
        merged_actions = []
        child_targets = {a.target for a in child.actions}
        
        # Add parent actions that aren't overridden
        for parent_action in parent.actions:
            if parent_action.target not in child_targets:
                merged_actions.append(parent_action)
        
        # Add all child actions
        merged_actions.extend(child.actions)
        merged_rule.actions = merged_actions
        
        # Merge tags
        merged_tags = list(set(parent.tags + child.tags))
        merged_rule.tags = merged_tags
        
        # Merge metadata
        merged_metadata = parent.metadata.copy() if parent.metadata else {}
        if child.metadata:
            merged_metadata.update(child.metadata)
        merged_rule.metadata = merged_metadata
        
        # Set inheritance metadata
        merged_rule.metadata = merged_rule.metadata or {}
        merged_rule.metadata['inherited_from'] = parent.id
        merged_rule.metadata['inheritance_merged'] = True
        
        return merged_rule
    
    def create_rule_override(self, base_rule_id: str, override_scope: RuleScope, 
                           context_filters: Dict[str, Any], 
                           override_actions: List[Dict[str, Any]],
                           created_by: str) -> str:
        """Create a rule override for specific scope and context"""
        
        # Get base rule
        base_rule = self._get_parent_rule(base_rule_id)
        if not base_rule:
            raise ValueError(f"Base rule {base_rule_id} not found")
        
        # Create override rule
        from .rules_engine import RuleCondition, RuleAction
        
        override_rule = Rule(
            id=f"{base_rule_id}_override_{override_scope.value}_{hash(json.dumps(context_filters, sort_keys=True))}",
            name=f"{base_rule.name} Override ({override_scope.value})",
            description=f"Override of {base_rule.name} for {override_scope.value} context",
            rule_type=base_rule.rule_type,
            scope=override_scope,
            priority=RulePriority.HIGH,  # Overrides get high priority
            status=base_rule.status,
            conditions=[RuleCondition(field=k, operator="eq", value=v) 
                       for k, v in context_filters.items()],
            actions=[RuleAction(**action) for action in override_actions],
            tags=base_rule.tags + ["override"],
            created_at=datetime.now(),
            created_by=created_by,
            updated_at=datetime.now(),
            updated_by=created_by,
            parent_rule_id=base_rule_id,
            conflict_resolution=ConflictResolution.MOST_SPECIFIC,
            metadata={"override_for": base_rule_id, "context_filters": context_filters}
        )
        
        # Store the override rule
        return self.rules_db.create_rule(override_rule)
    
    def validate_inheritance_chain(self, rule_id: str) -> Dict[str, Any]:
        """Validate inheritance chain for potential issues"""
        
        issues = []
        warnings = []
        
        rule = self._get_parent_rule(rule_id)
        if not rule:
            return {"valid": False, "error": f"Rule {rule_id} not found"}
        
        # Check for circular inheritance
        visited = set()
        current = rule
        while current and current.parent_rule_id:
            if current.id in visited:
                issues.append(f"Circular inheritance detected in chain: {' -> '.join(visited)}")
                break
            visited.add(current.id)
            current = self._get_parent_rule(current.parent_rule_id)
        
        # Check inheritance depth
        if len(visited) > 5:
            warnings.append(f"Inheritance chain is deep ({len(visited)} levels) - consider flattening")
        
        # Check scope consistency
        if rule.parent_rule_id:
            parent = self._get_parent_rule(rule.parent_rule_id)
            if parent:
                scope_hierarchy = [RuleScope.GLOBAL, RuleScope.PROJECT, RuleScope.MACHINE, RuleScope.AGENT, RuleScope.SESSION]
                parent_level = scope_hierarchy.index(parent.scope)
                child_level = scope_hierarchy.index(rule.scope)
                
                if child_level <= parent_level:
                    issues.append(f"Invalid scope inheritance: {rule.scope.value} inheriting from {parent.scope.value}")
        
        # Check for conflicting actions
        if rule.parent_rule_id:
            parent = self._get_parent_rule(rule.parent_rule_id)
            if parent:
                parent_targets = {a.target for a in parent.actions}
                child_targets = {a.target for a in rule.actions}
                conflicts = parent_targets.intersection(child_targets)
                
                if conflicts:
                    warnings.append(f"Actions override parent for targets: {', '.join(conflicts)}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "inheritance_depth": len(visited),
            "inheritance_chain": list(visited)
        }
    
    def get_inheritance_tree(self, root_rule_id: str) -> Dict[str, Any]:
        """Get complete inheritance tree starting from root rule"""
        
        def build_tree(rule_id: str, depth: int = 0) -> Dict[str, Any]:
            rule = self._get_parent_rule(rule_id)
            if not rule:
                return None
            
            # Find child rules
            children = self._get_child_rules(rule_id)
            
            return {
                "rule_id": rule_id,
                "name": rule.name,
                "scope": rule.scope.value,
                "priority": rule.priority.value,
                "depth": depth,
                "children": [build_tree(child.id, depth + 1) for child in children]
            }
        
        return build_tree(root_rule_id)
    
    def _get_child_rules(self, parent_rule_id: str) -> List[Rule]:
        """Get all direct child rules of a parent rule"""
        import sqlite3
        
        with sqlite3.connect(self.rules_db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM rules 
                WHERE parent_rule_id = ? AND status = 'active'
            """, (parent_rule_id,))
            
            return [self.rules_db._row_to_rule(row) for row in cursor.fetchall()]
    
    def suggest_inheritance_optimizations(self, rule_id: str) -> List[Dict[str, Any]]:
        """Suggest optimizations for rule inheritance structure"""
        
        suggestions = []
        
        # Validate inheritance chain
        validation = self.validate_inheritance_chain(rule_id)
        
        if validation["inheritance_depth"] > 3:
            suggestions.append({
                "type": "flatten_hierarchy",
                "message": f"Consider flattening inheritance hierarchy (depth: {validation['inheritance_depth']})",
                "recommendation": "Create specific rules instead of deep inheritance"
            })
        
        # Check for unused parent rules
        rule = self._get_parent_rule(rule_id)
        if rule and rule.parent_rule_id:
            parent = self._get_parent_rule(rule.parent_rule_id)
            if parent:
                children = self._get_child_rules(parent.id)
                if len(children) == 1:  # Only this rule inherits from parent
                    suggestions.append({
                        "type": "merge_parent",
                        "message": f"Parent rule {parent.id} only has one child",
                        "recommendation": "Consider merging parent and child rules"
                    })
        
        return suggestions