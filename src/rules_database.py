#!/usr/bin/env python3
"""
hAIveMind Rules Database and Management System
Comprehensive rule storage, versioning, and management capabilities

Author: Lance James, Unit 221B Inc
"""

import json
import sqlite3
import uuid
import yaml
import time
import hashlib
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

from .rules_engine import Rule, RuleType, RuleScope, RulePriority, RuleStatus, ConflictResolution, RuleCondition, RuleAction

logger = logging.getLogger(__name__)

class RuleChangeType(Enum):
    """Types of rule changes for version history"""
    CREATED = "created"
    UPDATED = "updated"
    ACTIVATED = "activated"
    DEACTIVATED = "deactivated"
    DEPRECATED = "deprecated"
    DELETED = "deleted"
    IMPORTED = "imported"
    EXPORTED = "exported"

@dataclass
class RuleCategory:
    """Rule category for organization"""
    id: str
    name: str
    description: str
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class RuleAssignment:
    """Rule assignment to specific scope targets"""
    id: str
    rule_id: str
    scope_type: str  # global, project, machine, agent, user
    scope_id: str    # specific ID for the scope
    priority_override: Optional[int] = None
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None
    metadata: Dict[str, Any] = None

@dataclass
class RuleVersion:
    """Rule version history entry"""
    id: str
    rule_id: str
    version: int
    change_type: RuleChangeType
    rule_data: Dict[str, Any]
    changed_by: str
    changed_at: datetime
    change_reason: Optional[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class RuleDependency:
    """Rule dependency relationship"""
    id: str
    rule_id: str
    depends_on_rule_id: str
    dependency_type: str  # requires, conflicts, enhances, replaces
    created_at: datetime
    metadata: Dict[str, Any] = None

@dataclass
class RuleTemplate:
    """Reusable rule template"""
    id: str
    name: str
    description: str
    rule_type: RuleType
    template_data: Dict[str, Any]
    category: str
    tags: List[str]
    created_by: str
    created_at: datetime
    metadata: Dict[str, Any] = None

class RulesDatabase:
    """Enhanced SQLite-based rules storage with comprehensive management features"""
    
    def __init__(self, db_path: str, chroma_client=None, redis_client=None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.chroma_client = chroma_client
        self.redis_client = redis_client
        self._init_database()
        self._init_default_categories()
        self._init_default_templates()
        
    def _init_database(self):
        """Initialize comprehensive rules database schema"""
        with sqlite3.connect(self.db_path) as conn:
            # Main rules table (enhanced)
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
                    effective_from TIMESTAMP,
                    effective_until TIMESTAMP,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (parent_rule_id) REFERENCES rules (id)
                )
            """)
            
            # Rule categories table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rule_categories (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT NOT NULL,
                    parent_id TEXT,
                    metadata TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (parent_id) REFERENCES rule_categories (id)
                )
            """)
            
            # Rule assignments table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rule_assignments (
                    id TEXT PRIMARY KEY,
                    rule_id TEXT NOT NULL,
                    scope_type TEXT NOT NULL,
                    scope_id TEXT NOT NULL,
                    priority_override INTEGER,
                    effective_from TIMESTAMP,
                    effective_until TIMESTAMP,
                    metadata TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (rule_id) REFERENCES rules (id),
                    UNIQUE(rule_id, scope_type, scope_id)
                )
            """)
            
            # Rule version history table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rule_versions (
                    id TEXT PRIMARY KEY,
                    rule_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    change_type TEXT NOT NULL,
                    rule_data TEXT NOT NULL,
                    changed_by TEXT NOT NULL,
                    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    change_reason TEXT,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (rule_id) REFERENCES rules (id)
                )
            """)
            
            # Rule dependencies table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rule_dependencies (
                    id TEXT PRIMARY KEY,
                    rule_id TEXT NOT NULL,
                    depends_on_rule_id TEXT NOT NULL,
                    dependency_type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (rule_id) REFERENCES rules (id),
                    FOREIGN KEY (depends_on_rule_id) REFERENCES rules (id),
                    UNIQUE(rule_id, depends_on_rule_id, dependency_type)
                )
            """)
            
            # Rule templates table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rule_templates (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT NOT NULL,
                    rule_type TEXT NOT NULL,
                    template_data TEXT NOT NULL,
                    category TEXT NOT NULL,
                    tags TEXT NOT NULL DEFAULT '[]',
                    created_by TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}'
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
            
            # Create comprehensive indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rules_type_scope ON rules (rule_type, scope)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rules_priority_status ON rules (priority, status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rules_effective_dates ON rules (effective_from, effective_until)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_assignments_scope ON rule_assignments (scope_type, scope_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_versions_rule_version ON rule_versions (rule_id, version)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_dependencies_rule ON rule_dependencies (rule_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_evaluations_rule_agent ON rule_evaluations (rule_id, agent_id)")
    
    def _init_default_categories(self):
        """Initialize default rule categories"""
        default_categories = [
            {"id": "authorship", "name": "Authorship Rules", "description": "Rules for code and content attribution"},
            {"id": "security", "name": "Security Rules", "description": "Security and safety enforcement rules"},
            {"id": "coding", "name": "Coding Standards", "description": "Code formatting and style rules"},
            {"id": "communication", "name": "Communication Rules", "description": "Response style and format rules"},
            {"id": "compliance", "name": "Compliance Rules", "description": "Regulatory and policy compliance rules"},
            {"id": "workflow", "name": "Workflow Rules", "description": "Development workflow and process rules"},
            {"id": "integration", "name": "Integration Rules", "description": "API and service integration rules"},
            {"id": "operational", "name": "Operational Rules", "description": "System operation and maintenance rules"}
        ]
        
        with sqlite3.connect(self.db_path) as conn:
            for category in default_categories:
                conn.execute("""
                    INSERT OR IGNORE INTO rule_categories (id, name, description)
                    VALUES (?, ?, ?)
                """, (category["id"], category["name"], category["description"]))
    
    def _init_default_templates(self):
        """Initialize default rule templates"""
        default_templates = [
            {
                "id": "authorship-template",
                "name": "Basic Authorship Rule",
                "description": "Template for setting code authorship",
                "rule_type": RuleType.AUTHORSHIP.value,
                "template_data": {
                    "name": "Set Author to {author_name}",
                    "description": "Ensure all work is attributed to {author_name}, {organization}",
                    "actions": [
                        {"action_type": "set", "target": "author", "value": "{author_name}"},
                        {"action_type": "set", "target": "organization", "value": "{organization}"}
                    ]
                },
                "category": "authorship",
                "tags": ["authorship", "attribution", "template"]
            },
            {
                "id": "security-no-secrets-template",
                "name": "No Secrets Exposure",
                "description": "Template for preventing secret exposure",
                "rule_type": RuleType.SECURITY.value,
                "template_data": {
                    "name": "Prevent Secret Exposure in {scope}",
                    "description": "Block exposure of secrets, keys, and sensitive data in {scope}",
                    "actions": [
                        {"action_type": "validate", "target": "code_content", "value": "no_secrets"},
                        {"action_type": "block", "target": "secret_exposure", "value": True}
                    ]
                },
                "category": "security",
                "tags": ["security", "secrets", "privacy", "template"]
            },
            {
                "id": "style-comments-template",
                "name": "Comment Policy",
                "description": "Template for code comment policies",
                "rule_type": RuleType.CODING_STYLE.value,
                "template_data": {
                    "name": "Comment Policy: {policy_type}",
                    "description": "Control when and how code comments are added",
                    "conditions": [
                        {"field": "task_type", "operator": "eq", "value": "code_generation"}
                    ],
                    "actions": [
                        {"action_type": "set", "target": "add_comments", "value": "{add_comments}"}
                    ]
                },
                "category": "coding",
                "tags": ["coding", "comments", "style", "template"]
            }
        ]
        
        with sqlite3.connect(self.db_path) as conn:
            for template in default_templates:
                conn.execute("""
                    INSERT OR IGNORE INTO rule_templates 
                    (id, name, description, rule_type, template_data, category, tags, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    template["id"], template["name"], template["description"],
                    template["rule_type"], json.dumps(template["template_data"]),
                    template["category"], json.dumps(template["tags"]), "system"
                ))
    
    def create_rule(self, rule: Rule, change_reason: Optional[str] = None) -> str:
        """Create a new rule with version tracking"""
        if not rule.id:
            rule.id = str(uuid.uuid4())
        
        rule_data = self._rule_to_dict(rule)
        
        with sqlite3.connect(self.db_path) as conn:
            # Insert the rule
            conn.execute("""
                INSERT INTO rules 
                (id, name, description, rule_type, scope, priority, status, conditions, actions, tags,
                 created_at, created_by, updated_at, updated_by, version, parent_rule_id, 
                 conflict_resolution, effective_from, effective_until, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, tuple(rule_data.values()))
            
            # Create version history entry
            version_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO rule_versions 
                (id, rule_id, version, change_type, rule_data, changed_by, change_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                version_id, rule.id, rule.version, RuleChangeType.CREATED.value,
                json.dumps(rule_data), rule.created_by, change_reason
            ))
        
        # Store rule in ChromaDB for semantic search
        if self.chroma_client:
            self._store_rule_embedding(rule)
        
        # Broadcast change to hAIveMind network
        if self.redis_client:
            self._broadcast_rule_change(rule.id, RuleChangeType.CREATED, rule_data)
        
        return rule.id
    
    def update_rule(self, rule: Rule, change_reason: Optional[str] = None) -> bool:
        """Update an existing rule with version tracking"""
        with sqlite3.connect(self.db_path) as conn:
            # Get current version
            cursor = conn.execute("SELECT version FROM rules WHERE id = ?", (rule.id,))
            current_version = cursor.fetchone()
            if not current_version:
                return False
            
            # Increment version
            rule.version = current_version[0] + 1
            rule.updated_at = datetime.now()
            
            rule_data = self._rule_to_dict(rule)
            
            # Update the rule
            conn.execute("""
                UPDATE rules SET 
                name = ?, description = ?, rule_type = ?, scope = ?, priority = ?, status = ?,
                conditions = ?, actions = ?, tags = ?, updated_at = ?, updated_by = ?, version = ?,
                parent_rule_id = ?, conflict_resolution = ?, effective_from = ?, effective_until = ?, metadata = ?
                WHERE id = ?
            """, (
                rule.name, rule.description, rule.rule_type.value, rule.scope.value,
                rule.priority.value, rule.status.value, json.dumps([asdict(c) for c in rule.conditions]),
                json.dumps([asdict(a) for a in rule.actions]), json.dumps(rule.tags),
                rule.updated_at.isoformat(), rule.updated_by, rule.version,
                rule.parent_rule_id, rule.conflict_resolution.value,
                rule.effective_from.isoformat() if rule.effective_from else None,
                rule.effective_until.isoformat() if rule.effective_until else None,
                json.dumps(rule.metadata or {}), rule.id
            ))
            
            # Create version history entry
            version_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO rule_versions 
                (id, rule_id, version, change_type, rule_data, changed_by, change_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                version_id, rule.id, rule.version, RuleChangeType.UPDATED.value,
                json.dumps(rule_data), rule.updated_by, change_reason
            ))
        
        # Update ChromaDB
        if self.chroma_client:
            self._update_rule_embedding(rule)
        
        # Broadcast change
        if self.redis_client:
            self._broadcast_rule_change(rule.id, RuleChangeType.UPDATED, rule_data)
        
        return True
    
    def activate_rule(self, rule_id: str, activated_by: str, effective_from: Optional[datetime] = None) -> bool:
        """Activate a rule with optional effective date"""
        return self._change_rule_status(rule_id, RuleStatus.ACTIVE, activated_by, 
                                       RuleChangeType.ACTIVATED, effective_from)
    
    def deactivate_rule(self, rule_id: str, deactivated_by: str, effective_until: Optional[datetime] = None) -> bool:
        """Deactivate a rule with optional effective date"""
        return self._change_rule_status(rule_id, RuleStatus.INACTIVE, deactivated_by, 
                                       RuleChangeType.DEACTIVATED, None, effective_until)
    
    def _change_rule_status(self, rule_id: str, new_status: RuleStatus, changed_by: str, 
                           change_type: RuleChangeType, effective_from: Optional[datetime] = None,
                           effective_until: Optional[datetime] = None) -> bool:
        """Change rule status with version tracking"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT version FROM rules WHERE id = ?", (rule_id,))
            current_version = cursor.fetchone()
            if not current_version:
                return False
            
            new_version = current_version[0] + 1
            
            conn.execute("""
                UPDATE rules SET status = ?, version = ?, updated_at = ?, updated_by = ?,
                                effective_from = ?, effective_until = ?
                WHERE id = ?
            """, (
                new_status.value, new_version, datetime.now().isoformat(), changed_by,
                effective_from.isoformat() if effective_from else None,
                effective_until.isoformat() if effective_until else None,
                rule_id
            ))
            
            # Create version history entry
            version_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO rule_versions 
                (id, rule_id, version, change_type, rule_data, changed_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                version_id, rule_id, new_version, change_type.value,
                json.dumps({"status": new_status.value, "effective_from": effective_from,
                          "effective_until": effective_until}), changed_by
            ))
        
        # Broadcast change
        if self.redis_client:
            self._broadcast_rule_change(rule_id, change_type, {"status": new_status.value})
        
        return True
    
    def get_rule_version_history(self, rule_id: str) -> List[RuleVersion]:
        """Get version history for a rule"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM rule_versions 
                WHERE rule_id = ? 
                ORDER BY version DESC
            """, (rule_id,))
            
            versions = []
            for row in cursor.fetchall():
                versions.append(RuleVersion(
                    id=row['id'],
                    rule_id=row['rule_id'],
                    version=row['version'],
                    change_type=RuleChangeType(row['change_type']),
                    rule_data=json.loads(row['rule_data']),
                    changed_by=row['changed_by'],
                    changed_at=datetime.fromisoformat(row['changed_at']),
                    change_reason=row['change_reason'],
                    metadata=json.loads(row['metadata']) if row['metadata'] else {}
                ))
            
            return versions
    
    def create_rule_dependency(self, rule_id: str, depends_on_rule_id: str, 
                              dependency_type: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a dependency relationship between rules"""
        dependency_id = str(uuid.uuid4())
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO rule_dependencies 
                (id, rule_id, depends_on_rule_id, dependency_type, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (
                dependency_id, rule_id, depends_on_rule_id, dependency_type,
                json.dumps(metadata or {})
            ))
        
        return dependency_id
    
    def get_rule_dependencies(self, rule_id: str) -> List[RuleDependency]:
        """Get all dependencies for a rule"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM rule_dependencies 
                WHERE rule_id = ? OR depends_on_rule_id = ?
                ORDER BY created_at
            """, (rule_id, rule_id))
            
            dependencies = []
            for row in cursor.fetchall():
                dependencies.append(RuleDependency(
                    id=row['id'],
                    rule_id=row['rule_id'],
                    depends_on_rule_id=row['depends_on_rule_id'],
                    dependency_type=row['dependency_type'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    metadata=json.loads(row['metadata']) if row['metadata'] else {}
                ))
            
            return dependencies
    
    def assign_rule_to_scope(self, rule_id: str, scope_type: str, scope_id: str,
                            priority_override: Optional[int] = None,
                            effective_from: Optional[datetime] = None,
                            effective_until: Optional[datetime] = None,
                            metadata: Optional[Dict[str, Any]] = None) -> str:
        """Assign a rule to a specific scope"""
        assignment_id = str(uuid.uuid4())
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO rule_assignments 
                (id, rule_id, scope_type, scope_id, priority_override, effective_from, effective_until, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                assignment_id, rule_id, scope_type, scope_id, priority_override,
                effective_from.isoformat() if effective_from else None,
                effective_until.isoformat() if effective_until else None,
                json.dumps(metadata or {})
            ))
        
        return assignment_id
    
    def export_rules(self, format: str = "yaml", rule_ids: Optional[List[str]] = None,
                     include_history: bool = False) -> str:
        """Export rules in YAML or JSON format"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if rule_ids:
                placeholders = ','.join(['?' for _ in rule_ids])
                cursor = conn.execute(f"SELECT * FROM rules WHERE id IN ({placeholders})", rule_ids)
            else:
                cursor = conn.execute("SELECT * FROM rules ORDER BY created_at")
            
            rules_data = []
            for row in cursor.fetchall():
                rule_dict = dict(row)
                rule_dict['conditions'] = json.loads(rule_dict['conditions'])
                rule_dict['actions'] = json.loads(rule_dict['actions'])
                rule_dict['tags'] = json.loads(rule_dict['tags'])
                rule_dict['metadata'] = json.loads(rule_dict['metadata'])
                
                if include_history:
                    rule_dict['version_history'] = [
                        asdict(v) for v in self.get_rule_version_history(rule_dict['id'])
                    ]
                
                rules_data.append(rule_dict)
        
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'format_version': '1.0',
            'rules': rules_data
        }
        
        if format.lower() == "yaml":
            return yaml.dump(export_data, default_flow_style=False, sort_keys=False)
        else:
            return json.dumps(export_data, indent=2, default=str)
    
    def import_rules(self, import_data: str, format: str = "yaml", 
                     imported_by: str = "system", overwrite: bool = False) -> List[str]:
        """Import rules from YAML or JSON format"""
        if format.lower() == "yaml":
            data = yaml.safe_load(import_data)
        else:
            data = json.loads(import_data)
        
        imported_rule_ids = []
        
        for rule_data in data.get('rules', []):
            # Convert dict back to Rule object
            rule = Rule(
                id=rule_data.get('id') or str(uuid.uuid4()),
                name=rule_data['name'],
                description=rule_data['description'],
                rule_type=RuleType(rule_data['rule_type']),
                scope=RuleScope(rule_data['scope']),
                priority=RulePriority(rule_data['priority']),
                status=RuleStatus(rule_data.get('status', 'active')),
                conditions=[RuleCondition(**c) for c in rule_data.get('conditions', [])],
                actions=[RuleAction(**a) for a in rule_data.get('actions', [])],
                tags=rule_data.get('tags', []),
                created_at=datetime.now(),
                created_by=imported_by,
                updated_at=datetime.now(),
                updated_by=imported_by,
                version=1,
                parent_rule_id=rule_data.get('parent_rule_id'),
                conflict_resolution=ConflictResolution(rule_data.get('conflict_resolution', 'highest_priority')),
                metadata=rule_data.get('metadata', {})
            )
            
            # Check if rule exists
            existing_rule = self.get_rule(rule.id)
            if existing_rule and not overwrite:
                logger.warning(f"Rule {rule.id} already exists, skipping import")
                continue
            
            if existing_rule and overwrite:
                self.update_rule(rule, f"Imported overwrite by {imported_by}")
            else:
                self.create_rule(rule, f"Imported by {imported_by}")
            
            imported_rule_ids.append(rule.id)
        
        return imported_rule_ids
    
    def create_rule_from_template(self, template_id: str, parameters: Dict[str, Any],
                                 created_by: str) -> Optional[str]:
        """Create a rule from a template with parameter substitution"""
        template = self.get_rule_template(template_id)
        if not template:
            return None
        
        # Substitute template parameters
        template_str = json.dumps(template.template_data)
        for key, value in parameters.items():
            template_str = template_str.replace(f"{{{key}}}", str(value))
        
        rule_data = json.loads(template_str)
        
        # Create rule from template
        rule = Rule(
            id=str(uuid.uuid4()),
            name=rule_data['name'],
            description=rule_data['description'],
            rule_type=template.rule_type,
            scope=RuleScope(parameters.get('scope', 'global')),
            priority=RulePriority(parameters.get('priority', 500)),
            status=RuleStatus.ACTIVE,
            conditions=[RuleCondition(**c) for c in rule_data.get('conditions', [])],
            actions=[RuleAction(**a) for a in rule_data.get('actions', [])],
            tags=rule_data.get('tags', []),
            created_at=datetime.now(),
            created_by=created_by,
            updated_at=datetime.now(),
            updated_by=created_by,
            version=1,
            metadata={'template_id': template_id, 'template_parameters': parameters}
        )
        
        return self.create_rule(rule, f"Created from template {template_id}")
    
    def get_rule_template(self, template_id: str) -> Optional[RuleTemplate]:
        """Get a rule template by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM rule_templates WHERE id = ?", (template_id,))
            row = cursor.fetchone()
            
            if row:
                return RuleTemplate(
                    id=row['id'],
                    name=row['name'],
                    description=row['description'],
                    rule_type=RuleType(row['rule_type']),
                    template_data=json.loads(row['template_data']),
                    category=row['category'],
                    tags=json.loads(row['tags']),
                    created_by=row['created_by'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    metadata=json.loads(row['metadata']) if row['metadata'] else {}
                )
        
        return None
    
    def list_rule_templates(self, category: Optional[str] = None) -> List[RuleTemplate]:
        """List available rule templates"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if category:
                cursor = conn.execute("SELECT * FROM rule_templates WHERE category = ? ORDER BY name", (category,))
            else:
                cursor = conn.execute("SELECT * FROM rule_templates ORDER BY category, name")
            
            templates = []
            for row in cursor.fetchall():
                templates.append(RuleTemplate(
                    id=row['id'],
                    name=row['name'],
                    description=row['description'],
                    rule_type=RuleType(row['rule_type']),
                    template_data=json.loads(row['template_data']),
                    category=row['category'],
                    tags=json.loads(row['tags']),
                    created_by=row['created_by'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    metadata=json.loads(row['metadata']) if row['metadata'] else {}
                ))
            
            return templates
    
    def backup_database(self, backup_path: str) -> bool:
        """Create a backup of the rules database"""
        try:
            backup_file = Path(backup_path)
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.db_path, backup_file)
            
            # Also export as YAML for human readability
            yaml_backup = backup_file.with_suffix('.yaml')
            with open(yaml_backup, 'w') as f:
                f.write(self.export_rules(format="yaml", include_history=True))
            
            return True
        except Exception as e:
            logger.error(f"Failed to backup database: {e}")
            return False
    
    def get_rule_statistics(self) -> Dict[str, Any]:
        """Get comprehensive rule statistics"""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}
            
            # Basic counts
            cursor = conn.execute("SELECT COUNT(*) FROM rules")
            stats['total_rules'] = cursor.fetchone()[0]
            
            # Rules by status
            cursor = conn.execute("SELECT status, COUNT(*) FROM rules GROUP BY status")
            stats['by_status'] = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Rules by type
            cursor = conn.execute("SELECT rule_type, COUNT(*) FROM rules GROUP BY rule_type")
            stats['by_type'] = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Rules by scope
            cursor = conn.execute("SELECT scope, COUNT(*) FROM rules GROUP BY scope")
            stats['by_scope'] = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Version statistics
            cursor = conn.execute("SELECT AVG(version), MAX(version) FROM rules")
            avg_version, max_version = cursor.fetchone()
            stats['version_stats'] = {'average': avg_version, 'maximum': max_version}
            
            # Recent activity
            cursor = conn.execute("""
                SELECT COUNT(*) FROM rule_versions 
                WHERE changed_at > datetime('now', '-7 days')
            """)
            stats['recent_changes'] = cursor.fetchone()[0]
            
            return stats
    
    def _rule_to_dict(self, rule: Rule) -> Dict[str, Any]:
        """Convert Rule object to dictionary for database storage"""
        return {
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
            'effective_from': getattr(rule, 'effective_from').isoformat() if hasattr(rule, 'effective_from') and getattr(rule, 'effective_from') else None,
            'effective_until': getattr(rule, 'effective_until').isoformat() if hasattr(rule, 'effective_until') and getattr(rule, 'effective_until') else None,
            'metadata': json.dumps(rule.metadata or {})
        }
    
    def _store_rule_embedding(self, rule: Rule):
        """Store rule in ChromaDB for semantic search"""
        try:
            collection = self.chroma_client.get_or_create_collection("rules")
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
    
    def _update_rule_embedding(self, rule: Rule):
        """Update rule embedding in ChromaDB"""
        try:
            collection = self.chroma_client.get_or_create_collection("rules")
            searchable_text = f"{rule.name} {rule.description} {' '.join(rule.tags)}"
            
            collection.update(
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
            logger.warning(f"Failed to update rule embedding: {e}")
    
    def _broadcast_rule_change(self, rule_id: str, change_type: RuleChangeType, rule_data: Dict[str, Any]):
        """Broadcast rule changes to hAIveMind network via Redis"""
        try:
            message = {
                'rule_id': rule_id,
                'change_type': change_type.value,
                'rule_data': rule_data,
                'timestamp': datetime.now().isoformat(),
                'machine_id': 'lance-dev'  # TODO: Get from config
            }
            self.redis_client.publish('haivemind:rules:changes', json.dumps(message))
        except Exception as e:
            logger.warning(f"Failed to broadcast rule change: {e}")
    
    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get a rule by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM rules WHERE id = ?", (rule_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_rule(row)
        
        return None
    
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