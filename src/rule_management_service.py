#!/usr/bin/env python3
"""
hAIveMind Rule Management Service
High-level service for comprehensive rule management operations

Author: Lance James, Unit 221B Inc
"""

import json
import yaml
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from pathlib import Path
import logging

from .rules_database import RulesDatabase, RuleChangeType
from .rules_engine import Rule, RuleType, RuleScope, RulePriority, RuleStatus, ConflictResolution, RuleCondition, RuleAction

logger = logging.getLogger(__name__)

class RuleValidationError(Exception):
    """Exception raised for rule validation errors"""
    pass

class RuleManagementService:
    """High-level service for rule management operations"""
    
    def __init__(self, db_path: str, chroma_client=None, redis_client=None):
        self.db = RulesDatabase(db_path, chroma_client, redis_client)
        self.chroma_client = chroma_client
        self.redis_client = redis_client
        
    def create_rule_from_dict(self, rule_data: Dict[str, Any], created_by: str) -> str:
        """Create a rule from dictionary data with validation"""
        # Validate required fields
        required_fields = ['name', 'description', 'rule_type']
        for field in required_fields:
            if field not in rule_data:
                raise RuleValidationError(f"Missing required field: {field}")
        
        # Set defaults
        rule_data.setdefault('id', str(uuid.uuid4()))
        rule_data.setdefault('scope', 'global')
        rule_data.setdefault('priority', 500)
        rule_data.setdefault('status', 'active')
        rule_data.setdefault('conditions', [])
        rule_data.setdefault('actions', [])
        rule_data.setdefault('tags', [])
        rule_data.setdefault('version', 1)
        rule_data.setdefault('conflict_resolution', 'highest_priority')
        rule_data.setdefault('metadata', {})
        
        # Create Rule object
        rule = Rule(
            id=rule_data['id'],
            name=rule_data['name'],
            description=rule_data['description'],
            rule_type=RuleType(rule_data['rule_type']),
            scope=RuleScope(rule_data['scope']),
            priority=RulePriority(rule_data['priority']),
            status=RuleStatus(rule_data['status']),
            conditions=[RuleCondition(**c) if isinstance(c, dict) else c for c in rule_data['conditions']],
            actions=[RuleAction(**a) if isinstance(a, dict) else a for a in rule_data['actions']],
            tags=rule_data['tags'],
            created_at=datetime.now(),
            created_by=created_by,
            updated_at=datetime.now(),
            updated_by=created_by,
            version=rule_data['version'],
            parent_rule_id=rule_data.get('parent_rule_id'),
            conflict_resolution=ConflictResolution(rule_data['conflict_resolution']),
            metadata=rule_data['metadata']
        )
        
        # Validate rule logic
        self._validate_rule_logic(rule)
        
        return self.db.create_rule(rule, "Created via rule management service")
    
    def create_rule_from_yaml(self, yaml_content: str, created_by: str) -> str:
        """Create a rule from YAML content"""
        try:
            rule_data = yaml.safe_load(yaml_content)
            return self.create_rule_from_dict(rule_data, created_by)
        except yaml.YAMLError as e:
            raise RuleValidationError(f"Invalid YAML format: {e}")
    
    def create_rule_from_json(self, json_content: str, created_by: str) -> str:
        """Create a rule from JSON content"""
        try:
            rule_data = json.loads(json_content)
            return self.create_rule_from_dict(rule_data, created_by)
        except json.JSONDecodeError as e:
            raise RuleValidationError(f"Invalid JSON format: {e}")
    
    def update_rule_from_dict(self, rule_id: str, rule_data: Dict[str, Any], updated_by: str) -> bool:
        """Update a rule from dictionary data"""
        existing_rule = self.db.get_rule(rule_id)
        if not existing_rule:
            raise RuleValidationError(f"Rule {rule_id} not found")
        
        # Update fields
        existing_rule.name = rule_data.get('name', existing_rule.name)
        existing_rule.description = rule_data.get('description', existing_rule.description)
        existing_rule.rule_type = RuleType(rule_data.get('rule_type', existing_rule.rule_type.value))
        existing_rule.scope = RuleScope(rule_data.get('scope', existing_rule.scope.value))
        existing_rule.priority = RulePriority(rule_data.get('priority', existing_rule.priority.value))
        existing_rule.status = RuleStatus(rule_data.get('status', existing_rule.status.value))
        existing_rule.conditions = [RuleCondition(**c) if isinstance(c, dict) else c 
                                   for c in rule_data.get('conditions', existing_rule.conditions)]
        existing_rule.actions = [RuleAction(**a) if isinstance(a, dict) else a 
                               for a in rule_data.get('actions', existing_rule.actions)]
        existing_rule.tags = rule_data.get('tags', existing_rule.tags)
        existing_rule.conflict_resolution = ConflictResolution(
            rule_data.get('conflict_resolution', existing_rule.conflict_resolution.value))
        existing_rule.metadata = rule_data.get('metadata', existing_rule.metadata)
        existing_rule.updated_by = updated_by
        
        # Validate updated rule
        self._validate_rule_logic(existing_rule)
        
        return self.db.update_rule(existing_rule, "Updated via rule management service")
    
    def get_rule_as_yaml(self, rule_id: str) -> Optional[str]:
        """Get a rule as YAML format"""
        rule = self.db.get_rule(rule_id)
        if not rule:
            return None
        
        rule_dict = self._rule_to_export_dict(rule)
        return yaml.dump(rule_dict, default_flow_style=False, sort_keys=False)
    
    def get_rule_as_json(self, rule_id: str, indent: int = 2) -> Optional[str]:
        """Get a rule as JSON format"""
        rule = self.db.get_rule(rule_id)
        if not rule:
            return None
        
        rule_dict = self._rule_to_export_dict(rule)
        return json.dumps(rule_dict, indent=indent, default=str)
    
    def _rule_to_export_dict(self, rule: Rule) -> Dict[str, Any]:
        """Convert Rule object to export dictionary"""
        return {
            'id': rule.id,
            'name': rule.name,
            'description': rule.description,
            'rule_type': rule.rule_type.value,
            'scope': rule.scope.value,
            'priority': rule.priority.value,
            'status': rule.status.value,
            'conditions': [self._condition_to_dict(c) for c in rule.conditions],
            'actions': [self._action_to_dict(a) for a in rule.actions],
            'tags': rule.tags,
            'created_at': rule.created_at.isoformat(),
            'created_by': rule.created_by,
            'updated_at': rule.updated_at.isoformat(),
            'updated_by': rule.updated_by,
            'version': rule.version,
            'parent_rule_id': rule.parent_rule_id,
            'conflict_resolution': rule.conflict_resolution.value,
            'metadata': rule.metadata
        }
    
    def _condition_to_dict(self, condition: RuleCondition) -> Dict[str, Any]:
        """Convert RuleCondition to dictionary"""
        return {
            'field': condition.field,
            'operator': condition.operator,
            'value': condition.value,
            'case_sensitive': condition.case_sensitive
        }
    
    def _action_to_dict(self, action: RuleAction) -> Dict[str, Any]:
        """Convert RuleAction to dictionary"""
        return {
            'action_type': action.action_type,
            'target': action.target,
            'value': action.value,
            'parameters': action.parameters
        }
    
    def _validate_rule_logic(self, rule: Rule):
        """Validate rule logic and conditions"""
        # Check for empty name or description
        if not rule.name.strip():
            raise RuleValidationError("Rule name cannot be empty")
        if not rule.description.strip():
            raise RuleValidationError("Rule description cannot be empty")
        
        # Validate conditions
        for i, condition in enumerate(rule.conditions):
            if not condition.field:
                raise RuleValidationError(f"Condition {i}: field cannot be empty")
            if not condition.operator:
                raise RuleValidationError(f"Condition {i}: operator cannot be empty")
            
            # Validate operators
            valid_operators = ['eq', 'ne', 'in', 'regex', 'contains', 'startswith', 'endswith', 'gt', 'lt', 'gte', 'lte']
            if condition.operator not in valid_operators:
                raise RuleValidationError(f"Condition {i}: invalid operator '{condition.operator}'")
            
            # Validate regex patterns
            if condition.operator == 'regex':
                try:
                    import re
                    re.compile(str(condition.value))
                except re.error as e:
                    raise RuleValidationError(f"Condition {i}: invalid regex pattern: {e}")
        
        # Validate actions
        for i, action in enumerate(rule.actions):
            if not action.action_type:
                raise RuleValidationError(f"Action {i}: action_type cannot be empty")
            if not action.target:
                raise RuleValidationError(f"Action {i}: target cannot be empty")
            
            # Validate action types
            valid_action_types = ['set', 'append', 'merge', 'validate', 'block', 'transform', 'invoke']
            if action.action_type not in valid_action_types:
                raise RuleValidationError(f"Action {i}: invalid action_type '{action.action_type}'")
    
    def activate_rule_with_schedule(self, rule_id: str, activated_by: str, 
                                   effective_from: Optional[datetime] = None,
                                   duration_hours: Optional[int] = None) -> bool:
        """Activate a rule with optional scheduling"""
        effective_until = None
        if duration_hours and effective_from:
            effective_until = effective_from + timedelta(hours=duration_hours)
        elif duration_hours:
            effective_until = datetime.now() + timedelta(hours=duration_hours)
        
        return self.db.activate_rule(rule_id, activated_by, effective_from)
    
    def create_rule_set(self, rule_set_data: Dict[str, Any], created_by: str) -> List[str]:
        """Create multiple related rules as a set"""
        rule_ids = []
        dependencies = rule_set_data.get('dependencies', [])
        
        # Create all rules first
        for rule_data in rule_set_data.get('rules', []):
            rule_id = self.create_rule_from_dict(rule_data, created_by)
            rule_ids.append(rule_id)
        
        # Create dependencies
        for dependency in dependencies:
            rule_id = dependency.get('rule_id')
            depends_on_id = dependency.get('depends_on_rule_id')
            dependency_type = dependency.get('type', 'requires')
            
            if rule_id and depends_on_id:
                self.db.create_rule_dependency(rule_id, depends_on_id, dependency_type)
        
        return rule_ids
    
    def get_conflicting_rules(self, rule: Rule, context: Dict[str, Any] = None) -> List[Rule]:
        """Find rules that would conflict with the given rule"""
        # Get all active rules that target the same behaviors
        conflicting_rules = []
        
        # This is a simplified implementation - in practice, you'd want more sophisticated conflict detection
        with self.db.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM rules 
                WHERE status = 'active' AND id != ? AND scope = ?
            """, (rule.id, rule.scope.value))
            
            for row in cursor.fetchall():
                existing_rule = self.db._row_to_rule(row)
                
                # Check if rules target overlapping behaviors
                existing_targets = {action.target for action in existing_rule.actions}
                new_targets = {action.target for action in rule.actions}
                
                if existing_targets.intersection(new_targets):
                    conflicting_rules.append(existing_rule)
        
        return conflicting_rules
    
    def suggest_rule_optimizations(self, rule_id: str) -> List[Dict[str, Any]]:
        """Suggest optimizations for a specific rule"""
        rule = self.db.get_rule(rule_id)
        if not rule:
            return []
        
        suggestions = []
        
        # Check for complex conditions
        if len(rule.conditions) > 5:
            suggestions.append({
                'type': 'complexity',
                'message': 'Rule has many conditions which may slow evaluation',
                'recommendation': 'Consider splitting into multiple rules or simplifying conditions'
            })
        
        # Check for regex conditions
        regex_conditions = [c for c in rule.conditions if c.operator == 'regex']
        if len(regex_conditions) > 2:
            suggestions.append({
                'type': 'performance',
                'message': 'Multiple regex conditions can be slow',
                'recommendation': 'Consider using simpler string operations where possible'
            })
        
        # Check for unused tags
        if not rule.tags:
            suggestions.append({
                'type': 'organization',
                'message': 'Rule has no tags for categorization',
                'recommendation': 'Add relevant tags to improve organization and searchability'
            })
        
        # Check rule age and usage
        age_days = (datetime.now() - rule.created_at).days
        if age_days > 30 and rule.version == 1:
            suggestions.append({
                'type': 'maintenance',
                'message': f'Rule is {age_days} days old with no updates',
                'recommendation': 'Review rule relevance and consider updates if needed'
            })
        
        return suggestions
    
    def bulk_import_rules(self, file_path: str, format: str = "auto", 
                         imported_by: str = "system", overwrite: bool = False) -> Dict[str, Any]:
        """Import rules from file with detailed results"""
        file_path = Path(file_path)
        
        if format == "auto":
            format = file_path.suffix.lower()[1:]  # Remove the dot
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            imported_rule_ids = self.db.import_rules(content, format, imported_by, overwrite)
            
            return {
                'success': True,
                'imported_count': len(imported_rule_ids),
                'imported_rule_ids': imported_rule_ids,
                'message': f"Successfully imported {len(imported_rule_ids)} rules"
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to import rules: {e}"
            }
    
    def bulk_export_rules(self, file_path: str, format: str = "yaml",
                         rule_ids: Optional[List[str]] = None,
                         include_history: bool = False) -> Dict[str, Any]:
        """Export rules to file with detailed results"""
        try:
            exported_data = self.db.export_rules(format, rule_ids, include_history)
            
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w') as f:
                f.write(exported_data)
            
            # Count rules in export
            if format.lower() == "yaml":
                data = yaml.safe_load(exported_data)
            else:
                data = json.loads(exported_data)
            
            rule_count = len(data.get('rules', []))
            
            return {
                'success': True,
                'exported_count': rule_count,
                'file_path': str(file_path),
                'format': format,
                'message': f"Successfully exported {rule_count} rules to {file_path}"
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to export rules: {e}"
            }
    
    def clone_rule(self, rule_id: str, new_name: str, cloned_by: str,
                  modifications: Optional[Dict[str, Any]] = None) -> str:
        """Clone a rule with optional modifications"""
        original_rule = self.db.get_rule(rule_id)
        if not original_rule:
            raise RuleValidationError(f"Rule {rule_id} not found")
        
        # Create clone data
        clone_data = self._rule_to_export_dict(original_rule)
        clone_data['id'] = str(uuid.uuid4())
        clone_data['name'] = new_name
        clone_data['parent_rule_id'] = rule_id  # Track the parent
        clone_data['created_at'] = datetime.now().isoformat()
        clone_data['created_by'] = cloned_by
        clone_data['updated_at'] = datetime.now().isoformat()
        clone_data['updated_by'] = cloned_by
        clone_data['version'] = 1
        
        # Apply modifications
        if modifications:
            for key, value in modifications.items():
                if key in clone_data and key not in ['id', 'parent_rule_id', 'created_at', 'created_by']:
                    clone_data[key] = value
        
        # Add clone metadata
        clone_data['metadata'] = clone_data.get('metadata', {})
        clone_data['metadata']['cloned_from'] = rule_id
        clone_data['metadata']['cloned_at'] = datetime.now().isoformat()
        
        return self.create_rule_from_dict(clone_data, cloned_by)
    
    def get_rule_inheritance_tree(self, rule_id: str) -> Dict[str, Any]:
        """Get the inheritance tree for a rule"""
        rule = self.db.get_rule(rule_id)
        if not rule:
            return {}
        
        # Get parent chain
        parent_chain = []
        current_rule = rule
        visited = set()  # Prevent infinite loops
        
        while current_rule and current_rule.parent_rule_id and current_rule.id not in visited:
            visited.add(current_rule.id)
            parent_rule = self.db.get_rule(current_rule.parent_rule_id)
            if parent_rule:
                parent_chain.append({
                    'id': parent_rule.id,
                    'name': parent_rule.name,
                    'rule_type': parent_rule.rule_type.value
                })
                current_rule = parent_rule
            else:
                break
        
        # Get children
        children = []
        with self.db.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT id, name, rule_type FROM rules WHERE parent_rule_id = ?
            """, (rule_id,))
            
            for row in cursor.fetchall():
                children.append({
                    'id': row['id'],
                    'name': row['name'],
                    'rule_type': row['rule_type']
                })
        
        return {
            'rule_id': rule_id,
            'rule_name': rule.name,
            'parents': parent_chain,
            'children': children,
            'depth': len(parent_chain)
        }
    
    def search_rules(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search rules using text search and filters"""
        results = []
        
        # Use ChromaDB for semantic search if available
        if self.chroma_client:
            try:
                collection = self.chroma_client.get_collection("rules")
                search_results = collection.query(
                    query_texts=[query],
                    n_results=20,
                    include=['metadatas', 'documents', 'distances']
                )
                
                for i, rule_id in enumerate(search_results['ids'][0]):
                    rule = self.db.get_rule(rule_id)
                    if rule and self._matches_filters(rule, filters):
                        results.append({
                            'rule': self._rule_to_export_dict(rule),
                            'relevance_score': 1.0 - search_results['distances'][0][i]
                        })
                
            except Exception as e:
                logger.warning(f"ChromaDB search failed, falling back to text search: {e}")
        
        # Fallback to SQL text search if no results or ChromaDB unavailable
        if not results:
            with self.db.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                sql_query = """
                    SELECT * FROM rules 
                    WHERE (name LIKE ? OR description LIKE ? OR tags LIKE ?)
                    ORDER BY priority DESC, created_at DESC
                """
                
                cursor = conn.execute(sql_query, (f"%{query}%", f"%{query}%", f"%{query}%"))
                
                for row in cursor.fetchall():
                    rule = self.db._row_to_rule(row)
                    if self._matches_filters(rule, filters):
                        results.append({
                            'rule': self._rule_to_export_dict(rule),
                            'relevance_score': 0.5  # Default relevance for text search
                        })
        
        return results
    
    def _matches_filters(self, rule: Rule, filters: Optional[Dict[str, Any]]) -> bool:
        """Check if rule matches the given filters"""
        if not filters:
            return True
        
        for key, value in filters.items():
            if key == 'rule_type' and rule.rule_type.value != value:
                return False
            elif key == 'scope' and rule.scope.value != value:
                return False
            elif key == 'status' and rule.status.value != value:
                return False
            elif key == 'priority' and rule.priority.value != value:
                return False
            elif key == 'tags' and not any(tag in rule.tags for tag in value if isinstance(value, list)):
                return False
            elif key == 'created_by' and rule.created_by != value:
                return False
        
        return True

    def get_connection(self):
        """Get database connection - delegated to the database"""
        return self.db.get_connection()