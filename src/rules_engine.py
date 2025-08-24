#!/usr/bin/env python3
"""
hAIveMind Rules Engine - Intelligent Agent Behavior Governance
Provides consistent rule-based behavior enforcement across the hAIveMind network

Author: Lance James, Unit 221B Inc
"""

import json
import time
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

class RuleType(Enum):
    """Rule classification types"""
    AUTHORSHIP = "authorship"
    CODING_STYLE = "coding_style"  
    SECURITY = "security"
    COMPLIANCE = "compliance"
    OPERATIONAL = "operational"
    COMMUNICATION = "communication"
    WORKFLOW = "workflow"
    INTEGRATION = "integration"

class RuleScope(Enum):
    """Rule application scope hierarchy"""
    GLOBAL = "global"           # Network-wide rules
    PROJECT = "project"         # Project-specific rules
    AGENT = "agent"            # Agent-specific rules
    MACHINE = "machine"        # Machine-specific rules
    SESSION = "session"        # Session-specific rules

class RulePriority(Enum):
    """Rule evaluation priority levels"""
    CRITICAL = 1000      # System-critical rules (security, compliance)
    HIGH = 750          # Important behavior rules (authorship, workflows)
    NORMAL = 500        # Standard preferences (coding style, communication)
    LOW = 250          # Convenience rules (operational preferences)
    ADVISORY = 100      # Suggestions and recommendations

class RuleStatus(Enum):
    """Rule lifecycle status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    TESTING = "testing"

class ConflictResolution(Enum):
    """Conflict resolution strategies"""
    HIGHEST_PRIORITY = "highest_priority"
    MOST_SPECIFIC = "most_specific"
    LATEST_CREATED = "latest_created"
    CONSENSUS = "consensus"
    OVERRIDE = "override"

@dataclass
class RuleCondition:
    """Rule application condition"""
    field: str                    # Field to evaluate (project, agent_role, etc.)
    operator: str                # Comparison operator (eq, ne, in, regex, etc.)
    value: Union[str, List[str]] # Expected value(s)
    case_sensitive: bool = True

@dataclass 
class RuleAction:
    """Rule enforcement action"""
    action_type: str             # Action to take (set, append, validate, etc.)
    target: str                  # Target field/behavior to modify
    value: Any                   # Action value
    parameters: Dict[str, Any] = None

@dataclass
class Rule:
    """hAIveMind governance rule definition"""
    id: str
    name: str
    description: str
    rule_type: RuleType
    scope: RuleScope
    priority: RulePriority
    status: RuleStatus
    conditions: List[RuleCondition]
    actions: List[RuleAction]
    tags: List[str]
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str
    version: int = 1
    parent_rule_id: Optional[str] = None  # For inheritance
    conflict_resolution: ConflictResolution = ConflictResolution.HIGHEST_PRIORITY
    metadata: Dict[str, Any] = None

class RulesDatabase:
    """SQLite-based rules storage with ChromaDB integration"""
    
    def __init__(self, db_path: str, chroma_client=None, redis_client=None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.chroma_client = chroma_client
        self.redis_client = redis_client
        self._init_database()
        
    def _init_database(self):
        """Initialize rules database schema"""
        import sqlite3
        
        with sqlite3.connect(self.db_path) as conn:
            # Rules table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rules (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    rule_type TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    conditions TEXT NOT NULL DEFAULT '[]',
                    actions TEXT NOT NULL DEFAULT '[]',
                    tags TEXT NOT NULL DEFAULT '[]',
                    created_at TIMESTAMP NOT NULL,
                    created_by TEXT NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    updated_by TEXT NOT NULL,
                    version INTEGER DEFAULT 1,
                    parent_rule_id TEXT,
                    conflict_resolution TEXT DEFAULT 'highest_priority',
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (parent_rule_id) REFERENCES rules (id)
                )
            """)
            
            # Rule evaluations table (for analytics)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rule_evaluations (
                    id TEXT PRIMARY KEY,
                    rule_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    machine_id TEXT NOT NULL,
                    evaluation_context TEXT NOT NULL,
                    result TEXT NOT NULL,
                    execution_time_ms INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (rule_id) REFERENCES rules (id)
                )
            """)
            
            # Rule conflicts table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rule_conflicts (
                    id TEXT PRIMARY KEY,
                    rule_ids TEXT NOT NULL,
                    conflict_type TEXT NOT NULL,
                    resolution_strategy TEXT NOT NULL,
                    resolved_rule_id TEXT,
                    context TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rules_type_scope ON rules (rule_type, scope)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rules_priority_status ON rules (priority, status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_evaluations_rule_agent ON rule_evaluations (rule_id, agent_id)")
            
            # Insert default hAIveMind rules
            self._create_default_rules(conn)
    
    def _create_default_rules(self, conn):
        """Create essential hAIveMind governance rules"""
        default_rules = [
            # Authorship Rules
            {
                "id": "auth-001",
                "name": "Default Authorship Attribution", 
                "description": "All work must be attributed to Lance James, Unit 221B Inc",
                "rule_type": RuleType.AUTHORSHIP.value,
                "scope": RuleScope.GLOBAL.value,
                "priority": RulePriority.CRITICAL.value,
                "conditions": json.dumps([]),
                "actions": json.dumps([
                    {"action_type": "set", "target": "author", "value": "Lance James"},
                    {"action_type": "set", "target": "organization", "value": "Unit 221B, Inc"},
                    {"action_type": "set", "target": "disable_ai_attribution", "value": True}
                ]),
                "tags": json.dumps(["authorship", "attribution", "global"])
            },
            
            # Security Rules  
            {
                "id": "sec-001",
                "name": "No Secret Exposure",
                "description": "Never expose or commit secrets, keys, passwords, or tokens",
                "rule_type": RuleType.SECURITY.value,
                "scope": RuleScope.GLOBAL.value,
                "priority": RulePriority.CRITICAL.value,
                "conditions": json.dumps([]),
                "actions": json.dumps([
                    {"action_type": "validate", "target": "code_content", "value": "no_secrets"},
                    {"action_type": "validate", "target": "commit_content", "value": "no_secrets"},
                    {"action_type": "block", "target": "secret_exposure", "value": True}
                ]),
                "tags": json.dumps(["security", "secrets", "privacy"])
            },
            
            {
                "id": "sec-002", 
                "name": "Defensive Security Only",
                "description": "Only assist with defensive security tasks, refuse malicious code",
                "rule_type": RuleType.SECURITY.value,
                "scope": RuleScope.GLOBAL.value,
                "priority": RulePriority.CRITICAL.value,
                "conditions": json.dumps([]),
                "actions": json.dumps([
                    {"action_type": "validate", "target": "code_intent", "value": "defensive_only"},
                    {"action_type": "block", "target": "malicious_code", "value": True}
                ]),
                "tags": json.dumps(["security", "defensive", "ethical"])
            },
            
            # Coding Style Rules
            {
                "id": "code-001",
                "name": "Minimal Comments Policy", 
                "description": "Do not add comments unless explicitly requested by user",
                "rule_type": RuleType.CODING_STYLE.value,
                "scope": RuleScope.GLOBAL.value,
                "priority": RulePriority.HIGH.value,
                "conditions": json.dumps([]),
                "actions": json.dumps([
                    {"action_type": "set", "target": "add_comments", "value": False},
                    {"action_type": "validate", "target": "user_comment_request", "value": "explicit"}
                ]),
                "tags": json.dumps(["coding", "comments", "style"])
            },
            
            # Communication Rules
            {
                "id": "comm-001",
                "name": "Concise Response Style",
                "description": "Keep responses short, direct, and to the point unless detail requested", 
                "rule_type": RuleType.COMMUNICATION.value,
                "scope": RuleScope.GLOBAL.value,
                "priority": RulePriority.NORMAL.value,
                "conditions": json.dumps([]),
                "actions": json.dumps([
                    {"action_type": "set", "target": "response_style", "value": "concise"},
                    {"action_type": "set", "target": "max_response_lines", "value": 4},
                    {"action_type": "set", "target": "avoid_preamble", "value": True}
                ]),
                "tags": json.dumps(["communication", "style", "brevity"])
            },
            
            {
                "id": "comm-002",
                "name": "No Emojis Default",
                "description": "Only use emojis when explicitly requested by user",
                "rule_type": RuleType.COMMUNICATION.value,
                "scope": RuleScope.GLOBAL.value,
                "priority": RulePriority.HIGH.value,
                "conditions": json.dumps([]),
                "actions": json.dumps([
                    {"action_type": "set", "target": "use_emojis", "value": False},
                    {"action_type": "validate", "target": "user_emoji_request", "value": "explicit"}
                ]),
                "tags": json.dumps(["communication", "emojis", "formatting"])
            }
        ]
        
        # Insert default rules if they don't exist
        for rule_data in default_rules:
            rule_data.update({
                "created_at": datetime.now().isoformat(),
                "created_by": "system",
                "updated_at": datetime.now().isoformat(), 
                "updated_by": "system",
                "status": RuleStatus.ACTIVE.value,
                "metadata": "{}"
            })
            
            conn.execute("""
                INSERT OR IGNORE INTO rules 
                (id, name, description, rule_type, scope, priority, status, conditions, actions, tags,
                 created_at, created_by, updated_at, updated_by, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rule_data["id"], rule_data["name"], rule_data["description"],
                rule_data["rule_type"], rule_data["scope"], rule_data["priority"],
                rule_data["status"], rule_data["conditions"], rule_data["actions"],
                rule_data["tags"], rule_data["created_at"], rule_data["created_by"],
                rule_data["updated_at"], rule_data["updated_by"], rule_data["metadata"]
            ))

    def create_rule(self, rule: Rule) -> str:
        """Create a new rule"""
        import sqlite3
        
        if not rule.id:
            rule.id = str(uuid.uuid4())
            
        rule_data = {
            'id': rule.id,
            'name': rule.name,
            'description': rule.description,
            'rule_type': rule.rule_type.value,
            'scope': rule.scope.value,
            'priority': rule.priority.value,
            'status': rule.status.value,
            'conditions': json.dumps([asdict(c) for c in rule.conditions]),
            'actions': json.dumps([asdict(a) for a in rule.actions]),
            'tags': json.dumps(rule.tags),
            'created_at': rule.created_at.isoformat(),
            'created_by': rule.created_by,
            'updated_at': rule.updated_at.isoformat(),
            'updated_by': rule.updated_by,
            'version': rule.version,
            'parent_rule_id': rule.parent_rule_id,
            'conflict_resolution': rule.conflict_resolution.value,
            'metadata': json.dumps(rule.metadata or {})
        }
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO rules 
                (id, name, description, rule_type, scope, priority, status, conditions, actions, tags,
                 created_at, created_by, updated_at, updated_by, version, parent_rule_id, 
                 conflict_resolution, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, tuple(rule_data.values()))
            
        # Store rule in ChromaDB for semantic search
        if self.chroma_client:
            self._store_rule_embedding(rule)
            
        return rule.id

    def _store_rule_embedding(self, rule: Rule):
        """Store rule in ChromaDB for semantic search"""
        try:
            collection = self.chroma_client.get_or_create_collection("rules")
            
            # Create searchable text from rule
            searchable_text = f"{rule.name} {rule.description} {' '.join(rule.tags)}"
            
            collection.add(
                documents=[searchable_text],
                metadatas=[{
                    "rule_id": rule.id,
                    "rule_type": rule.rule_type.value,
                    "scope": rule.scope.value,
                    "priority": rule.priority.value,
                    "status": rule.status.value
                }],
                ids=[rule.id]
            )
        except Exception as e:
            logger.warning(f"Failed to store rule embedding: {e}")

    def get_applicable_rules(self, context: Dict[str, Any]) -> List[Rule]:
        """Get rules applicable to given context, sorted by priority"""
        import sqlite3
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM rules 
                WHERE status = 'active'
                ORDER BY priority DESC, created_at ASC
            """)
            
            all_rules = []
            for row in cursor.fetchall():
                rule = self._row_to_rule(row)
                if self._rule_matches_context(rule, context):
                    all_rules.append(rule)
                    
            return all_rules

    def _row_to_rule(self, row) -> Rule:
        """Convert database row to Rule object"""
        return Rule(
            id=row['id'],
            name=row['name'],
            description=row['description'],
            rule_type=RuleType(row['rule_type']),
            scope=RuleScope(row['scope']),
            priority=RulePriority(row['priority']),
            status=RuleStatus(row['status']),
            conditions=[RuleCondition(**c) for c in json.loads(row['conditions'])],
            actions=[RuleAction(**a) for a in json.loads(row['actions'])],
            tags=json.loads(row['tags']),
            created_at=datetime.fromisoformat(row['created_at']),
            created_by=row['created_by'],
            updated_at=datetime.fromisoformat(row['updated_at']),
            updated_by=row['updated_by'],
            version=row['version'],
            parent_rule_id=row['parent_rule_id'],
            conflict_resolution=ConflictResolution(row['conflict_resolution']),
            metadata=json.loads(row['metadata'])
        )

    def _rule_matches_context(self, rule: Rule, context: Dict[str, Any]) -> bool:
        """Check if rule conditions match the given context"""
        if not rule.conditions:
            return True  # No conditions means always applicable
            
        for condition in rule.conditions:
            if not self._evaluate_condition(condition, context):
                return False
                
        return True

    def _evaluate_condition(self, condition: RuleCondition, context: Dict[str, Any]) -> bool:
        """Evaluate a single rule condition against context"""
        field_value = context.get(condition.field)
        
        if field_value is None:
            return False
            
        # Handle case sensitivity
        if isinstance(field_value, str) and isinstance(condition.value, str):
            if not condition.case_sensitive:
                field_value = field_value.lower()
                condition.value = condition.value.lower()
        
        # Evaluate operators
        if condition.operator == "eq":
            return field_value == condition.value
        elif condition.operator == "ne":
            return field_value != condition.value
        elif condition.operator == "in":
            return field_value in condition.value
        elif condition.operator == "regex":
            return bool(re.match(condition.value, str(field_value)))
        elif condition.operator == "contains":
            return str(condition.value) in str(field_value)
        elif condition.operator == "startswith":
            return str(field_value).startswith(str(condition.value))
        elif condition.operator == "endswith":
            return str(field_value).endswith(str(condition.value))
            
        return False


class RulesEngine:
    """hAIveMind Rules Engine - Behavior governance and enforcement"""
    
    def __init__(self, db_path: str, chroma_client=None, redis_client=None, config: Dict[str, Any] = None):
        self.db = RulesDatabase(db_path, chroma_client, redis_client)
        self.redis_client = redis_client
        self.config = config or {}
        self.evaluation_cache = {}
        
    def evaluate_rules(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate all applicable rules and return consolidated behavior configuration"""
        start_time = time.time()
        
        # Get applicable rules
        applicable_rules = self.db.get_applicable_rules(context)
        
        # Resolve conflicts and build configuration
        configuration = self._build_configuration(applicable_rules, context)
        
        # Cache evaluation result
        context_hash = hashlib.md5(json.dumps(context, sort_keys=True).encode()).hexdigest()
        evaluation_time = int((time.time() - start_time) * 1000)
        
        # Log evaluation for analytics
        self._log_evaluation(applicable_rules, context, configuration, evaluation_time)
        
        return {
            'configuration': configuration,
            'applied_rules': [r.id for r in applicable_rules],
            'evaluation_time_ms': evaluation_time,
            'context_hash': context_hash
        }

    def _build_configuration(self, rules: List[Rule], context: Dict[str, Any]) -> Dict[str, Any]:
        """Build consolidated configuration from applicable rules"""
        config = {}
        rule_applications = []
        
        # Group rules by target and resolve conflicts
        target_rules = {}
        for rule in rules:
            for action in rule.actions:
                target = action.target
                if target not in target_rules:
                    target_rules[target] = []
                target_rules[target].append((rule, action))
        
        # Apply rules to build configuration
        for target, rule_action_pairs in target_rules.items():
            if len(rule_action_pairs) == 1:
                # No conflict, apply directly
                rule, action = rule_action_pairs[0]
                config[target] = self._apply_action(action, config.get(target))
                rule_applications.append({'rule_id': rule.id, 'target': target, 'action': action.action_type})
            else:
                # Resolve conflict
                resolved_rule, resolved_action = self._resolve_conflict(rule_action_pairs, context)
                config[target] = self._apply_action(resolved_action, config.get(target))
                rule_applications.append({
                    'rule_id': resolved_rule.id, 
                    'target': target, 
                    'action': resolved_action.action_type,
                    'conflict_resolved': True
                })
        
        config['_rule_applications'] = rule_applications
        return config

    def _resolve_conflict(self, rule_action_pairs: List[Tuple[Rule, RuleAction]], context: Dict[str, Any]) -> Tuple[Rule, RuleAction]:
        """Resolve conflicts between multiple rules targeting same behavior"""
        if len(rule_action_pairs) == 1:
            return rule_action_pairs[0]
        
        # Get primary conflict resolution strategy from highest priority rule
        primary_strategy = rule_action_pairs[0][0].conflict_resolution
        
        if primary_strategy == ConflictResolution.HIGHEST_PRIORITY:
            # Sort by priority and return highest
            sorted_pairs = sorted(rule_action_pairs, key=lambda x: x[0].priority.value, reverse=True)
            return sorted_pairs[0]
            
        elif primary_strategy == ConflictResolution.MOST_SPECIFIC:
            # Prefer more specific scopes (agent > project > global)
            scope_priority = {RuleScope.AGENT: 3, RuleScope.PROJECT: 2, RuleScope.GLOBAL: 1}
            sorted_pairs = sorted(rule_action_pairs, 
                                key=lambda x: scope_priority.get(x[0].scope, 0), reverse=True)
            return sorted_pairs[0]
            
        elif primary_strategy == ConflictResolution.LATEST_CREATED:
            # Use most recently created rule
            sorted_pairs = sorted(rule_action_pairs, key=lambda x: x[0].created_at, reverse=True)
            return sorted_pairs[0]
        
        # Default to highest priority
        sorted_pairs = sorted(rule_action_pairs, key=lambda x: x[0].priority.value, reverse=True)
        return sorted_pairs[0]

    def _apply_action(self, action: RuleAction, current_value: Any = None) -> Any:
        """Apply rule action to generate configuration value"""
        if action.action_type == "set":
            return action.value
        elif action.action_type == "append" and isinstance(current_value, list):
            return current_value + [action.value]
        elif action.action_type == "merge" and isinstance(current_value, dict):
            result = current_value.copy()
            result.update(action.value)
            return result
        elif action.action_type == "validate":
            return {"validation": action.value, "current": current_value}
        elif action.action_type == "block":
            return {"blocked": True, "reason": action.value}
        else:
            return action.value

    def _log_evaluation(self, rules: List[Rule], context: Dict[str, Any], result: Dict[str, Any], execution_time: int):
        """Log rule evaluation for analytics"""
        import sqlite3
        
        evaluation_id = str(uuid.uuid4())
        agent_id = context.get('agent_id', 'unknown')
        machine_id = context.get('machine_id', 'unknown')
        
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                conn.execute("""
                    INSERT INTO rule_evaluations 
                    (id, rule_id, agent_id, machine_id, evaluation_context, result, execution_time_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    evaluation_id,
                    json.dumps([r.id for r in rules]),
                    agent_id,
                    machine_id,
                    json.dumps(context),
                    json.dumps(result),
                    execution_time
                ))
        except Exception as e:
            logger.warning(f"Failed to log rule evaluation: {e}")

    def get_rule_analytics(self, rule_id: Optional[str] = None, days: int = 7) -> Dict[str, Any]:
        """Get rule performance analytics"""
        import sqlite3
        
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Base query
            base_query = """
                SELECT * FROM rule_evaluations 
                WHERE created_at > datetime('now', '-{} days')
            """.format(days)
            
            if rule_id:
                base_query += " AND rule_id = ?"
                params = (rule_id,)
            else:
                params = ()
            
            cursor = conn.execute(base_query, params)
            evaluations = cursor.fetchall()
            
            # Calculate analytics
            total_evaluations = len(evaluations)
            avg_execution_time = sum(e['execution_time_ms'] for e in evaluations) / total_evaluations if total_evaluations > 0 else 0
            
            # Agent usage patterns
            agent_usage = {}
            machine_usage = {}
            
            for eval in evaluations:
                agent_id = eval['agent_id']
                machine_id = eval['machine_id']
                
                agent_usage[agent_id] = agent_usage.get(agent_id, 0) + 1
                machine_usage[machine_id] = machine_usage.get(machine_id, 0) + 1
            
            return {
                'total_evaluations': total_evaluations,
                'average_execution_time_ms': avg_execution_time,
                'agent_usage_patterns': agent_usage,
                'machine_usage_patterns': machine_usage,
                'period_days': days
            }

    def suggest_rule_optimizations(self) -> List[Dict[str, Any]]:
        """Analyze rule performance and suggest optimizations"""
        analytics = self.get_rule_analytics(days=30)
        suggestions = []
        
        # Slow rules
        if analytics['average_execution_time_ms'] > 100:
            suggestions.append({
                'type': 'performance',
                'message': 'Rule evaluation is slower than optimal (>100ms average)',
                'recommendation': 'Consider simplifying rule conditions or adding caching'
            })
        
        # Unused rules
        for rule_id in self.db.get_all_rule_ids():
            rule_analytics = self.get_rule_analytics(rule_id=rule_id, days=30)
            if rule_analytics['total_evaluations'] == 0:
                suggestions.append({
                    'type': 'unused',
                    'rule_id': rule_id,
                    'message': f'Rule {rule_id} has not been evaluated in 30 days',
                    'recommendation': 'Consider archiving or removing unused rule'
                })
        
        return suggestions