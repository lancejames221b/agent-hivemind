#!/usr/bin/env python3
"""
Rule Template System for hAIveMind Rules Engine
Provides template management, versioning, and marketplace capabilities

Author: Lance James, Unit 221B Inc
"""

import json
import uuid
import yaml
import hashlib
import shutil
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
try:
    import semver
    SEMVER_AVAILABLE = True
except ImportError:
    SEMVER_AVAILABLE = False
    semver = None

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None
try:
    from jinja2 import Template, Environment, BaseLoader
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False
    Template = Environment = BaseLoader = None

from rules_engine import Rule, RuleType, RuleScope, RulePriority, RuleStatus, RuleCondition, RuleAction
from advanced_rule_types import AdvancedRuleType, ComplianceFramework

logger = logging.getLogger(__name__)

class TemplateCategory(Enum):
    """Template categories for organization"""
    DEVOPS = "devops"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    CODING = "coding"
    COMMUNICATION = "communication"
    WORKFLOW = "workflow"
    INTEGRATION = "integration"
    INDUSTRY_SPECIFIC = "industry_specific"
    CUSTOM = "custom"

class TemplateStatus(Enum):
    """Template lifecycle status"""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    COMMUNITY = "community"
    VERIFIED = "verified"

class IndustryType(Enum):
    """Industry-specific template types"""
    HEALTHCARE = "healthcare"
    FINANCE = "finance"
    GOVERNMENT = "government"
    EDUCATION = "education"
    RETAIL = "retail"
    MANUFACTURING = "manufacturing"
    TECHNOLOGY = "technology"
    GENERIC = "generic"

@dataclass
class TemplateParameter:
    """Template parameter definition"""
    name: str
    type: str  # string, integer, boolean, list, dict
    description: str
    required: bool = True
    default_value: Any = None
    validation_pattern: Optional[str] = None
    allowed_values: Optional[List[Any]] = None

@dataclass
class TemplateMetadata:
    """Template metadata and versioning information"""
    id: str
    name: str
    description: str
    version: str
    author: str
    organization: str
    category: TemplateCategory
    industry: IndustryType
    status: TemplateStatus
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    download_count: int = 0
    rating: float = 0.0
    rating_count: int = 0
    license: str = "MIT"
    dependencies: List[str] = None
    compatibility: Dict[str, str] = None

@dataclass
class RuleTemplate:
    """Complete rule template with metadata and content"""
    metadata: TemplateMetadata
    parameters: List[TemplateParameter]
    template_content: Dict[str, Any]
    examples: List[Dict[str, Any]] = None
    documentation: str = ""
    test_cases: List[Dict[str, Any]] = None
    validation_schema: Dict[str, Any] = None

@dataclass
class TemplatePackage:
    """Collection of related templates"""
    id: str
    name: str
    description: str
    version: str
    templates: List[str]  # Template IDs
    dependencies: List[str] = None
    installation_script: Optional[str] = None
    metadata: Dict[str, Any] = None

class RuleTemplateSystem:
    """Comprehensive rule template management system"""
    
    def __init__(self, db_path: str, templates_dir: str, memory_storage, config: Dict[str, Any]):
        self.db_path = Path(db_path)
        self.templates_dir = Path(templates_dir)
        self.memory_storage = memory_storage
        self.config = config
        
        # Create directories
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        (self.templates_dir / "community").mkdir(exist_ok=True)
        (self.templates_dir / "custom").mkdir(exist_ok=True)
        (self.templates_dir / "packages").mkdir(exist_ok=True)
        
        # Initialize template database
        self._init_template_database()
        
        # Load built-in templates
        self._load_builtin_templates()
        
        # Initialize Jinja2 environment
        if JINJA2_AVAILABLE:
            self.jinja_env = Environment(loader=BaseLoader())
        else:
            self.jinja_env = None
            logger.warning("Jinja2 not available, template rendering will be limited")
    
    def _init_template_database(self):
        """Initialize template database schema"""
        import sqlite3
        
        with sqlite3.connect(self.db_path) as conn:
            # Templates table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rule_templates (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    version TEXT NOT NULL,
                    author TEXT NOT NULL,
                    organization TEXT NOT NULL,
                    category TEXT NOT NULL,
                    industry TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    tags TEXT NOT NULL DEFAULT '[]',
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    download_count INTEGER DEFAULT 0,
                    rating REAL DEFAULT 0.0,
                    rating_count INTEGER DEFAULT 0,
                    license TEXT DEFAULT 'MIT',
                    dependencies TEXT DEFAULT '[]',
                    compatibility TEXT DEFAULT '{}',
                    template_content TEXT NOT NULL,
                    parameters TEXT NOT NULL DEFAULT '[]',
                    examples TEXT DEFAULT '[]',
                    documentation TEXT DEFAULT '',
                    test_cases TEXT DEFAULT '[]',
                    validation_schema TEXT DEFAULT '{}'
                )
            """)
            
            # Template packages table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS template_packages (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    version TEXT NOT NULL,
                    templates TEXT NOT NULL DEFAULT '[]',
                    dependencies TEXT DEFAULT '[]',
                    installation_script TEXT,
                    metadata TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Template usage tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS template_usage (
                    id TEXT PRIMARY KEY,
                    template_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    machine_id TEXT NOT NULL,
                    parameters TEXT NOT NULL,
                    created_rule_id TEXT,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (template_id) REFERENCES rule_templates (id)
                )
            """)
            
            # Template ratings
            conn.execute("""
                CREATE TABLE IF NOT EXISTS template_ratings (
                    id TEXT PRIMARY KEY,
                    template_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                    review TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (template_id) REFERENCES rule_templates (id),
                    UNIQUE(template_id, user_id)
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_templates_category ON rule_templates (category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_templates_industry ON rule_templates (industry)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_templates_status ON rule_templates (status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_templates_rating ON rule_templates (rating DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_template ON template_usage (template_id)")
    
    def _load_builtin_templates(self):
        """Load built-in rule templates"""
        builtin_templates = [
            self._create_authorship_template(),
            self._create_security_no_secrets_template(),
            self._create_gdpr_compliance_template(),
            self._create_soc2_compliance_template(),
            self._create_hipaa_compliance_template(),
            self._create_code_quality_template(),
            self._create_devops_workflow_template(),
            self._create_security_adaptive_template(),
            self._create_time_based_maintenance_template(),
            self._create_context_aware_response_template()
        ]
        
        for template in builtin_templates:
            self.create_template(template, overwrite=True)
    
    def create_template(self, template: RuleTemplate, overwrite: bool = False) -> str:
        """Create a new rule template"""
        import sqlite3
        
        # Check if template exists
        if not overwrite and self.get_template(template.metadata.id):
            raise ValueError(f"Template {template.metadata.id} already exists")
        
        # Validate template
        validation_result = self._validate_template(template)
        if not validation_result['valid']:
            raise ValueError(f"Template validation failed: {validation_result['errors']}")
        
        # Store template in database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO rule_templates 
                (id, name, description, version, author, organization, category, industry, status, tags,
                 created_at, updated_at, license, dependencies, compatibility, template_content, 
                 parameters, examples, documentation, test_cases, validation_schema)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                template.metadata.id, template.metadata.name, template.metadata.description,
                template.metadata.version, template.metadata.author, template.metadata.organization,
                template.metadata.category.value, template.metadata.industry.value,
                template.metadata.status.value, json.dumps(template.metadata.tags),
                template.metadata.created_at.isoformat(), template.metadata.updated_at.isoformat(),
                template.metadata.license, json.dumps(template.metadata.dependencies or []),
                json.dumps(template.metadata.compatibility or {}),
                json.dumps(template.template_content),
                json.dumps([asdict(p) for p in template.parameters]),
                json.dumps(template.examples or []),
                template.documentation,
                json.dumps(template.test_cases or []),
                json.dumps(template.validation_schema or {})
            ))
        
        # Store template file
        template_file = self.templates_dir / f"{template.metadata.id}.yaml"
        with open(template_file, 'w') as f:
            yaml.dump(asdict(template), f, default_flow_style=False)
        
        # Store in hAIveMind memory
        self.memory_storage.store_memory(
            content=f"Created rule template: {template.metadata.name}",
            category="templates",
            metadata={
                'template_id': template.metadata.id,
                'category': template.metadata.category.value,
                'industry': template.metadata.industry.value,
                'version': template.metadata.version
            }
        )
        
        return template.metadata.id
    
    def instantiate_template(self, template_id: str, parameters: Dict[str, Any], 
                           created_by: str) -> Optional[Rule]:
        """Create a rule instance from template"""
        template = self.get_template(template_id)
        if not template:
            return None
        
        # Validate parameters
        param_validation = self._validate_parameters(template, parameters)
        if not param_validation['valid']:
            raise ValueError(f"Parameter validation failed: {param_validation['errors']}")
        
        # Render template with parameters
        rendered_content = self._render_template(template, parameters)
        
        # Create rule from rendered content
        rule = self._create_rule_from_rendered_content(rendered_content, created_by)
        
        # Track template usage
        self._track_template_usage(template_id, parameters, created_by, rule.id, True)
        
        return rule
    
    def get_template(self, template_id: str) -> Optional[RuleTemplate]:
        """Get template by ID"""
        import sqlite3
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM rule_templates WHERE id = ?", (template_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_template(row)
        
        return None
    
    def search_templates(self, query: str = "", category: Optional[TemplateCategory] = None,
                        industry: Optional[IndustryType] = None, tags: List[str] = None,
                        min_rating: float = 0.0, limit: int = 50) -> List[RuleTemplate]:
        """Search templates with filters"""
        import sqlite3
        
        conditions = []
        params = []
        
        if query:
            conditions.append("(name LIKE ? OR description LIKE ? OR tags LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])
        
        if category:
            conditions.append("category = ?")
            params.append(category.value)
        
        if industry:
            conditions.append("industry = ?")
            params.append(industry.value)
        
        if tags:
            for tag in tags:
                conditions.append("tags LIKE ?")
                params.append(f"%{tag}%")
        
        if min_rating > 0:
            conditions.append("rating >= ?")
            params.append(min_rating)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(f"""
                SELECT * FROM rule_templates 
                WHERE {where_clause} AND status IN ('active', 'verified', 'community')
                ORDER BY rating DESC, download_count DESC
                LIMIT ?
            """, params + [limit])
            
            templates = []
            for row in cursor.fetchall():
                templates.append(self._row_to_template(row))
            
            return templates
    
    def get_popular_templates(self, limit: int = 10) -> List[RuleTemplate]:
        """Get most popular templates"""
        import sqlite3
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM rule_templates 
                WHERE status IN ('active', 'verified', 'community')
                ORDER BY download_count DESC, rating DESC
                LIMIT ?
            """, (limit,))
            
            templates = []
            for row in cursor.fetchall():
                templates.append(self._row_to_template(row))
            
            return templates
    
    def rate_template(self, template_id: str, user_id: str, rating: int, review: str = "") -> bool:
        """Rate a template"""
        import sqlite3
        
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")
        
        with sqlite3.connect(self.db_path) as conn:
            # Insert or update rating
            conn.execute("""
                INSERT OR REPLACE INTO template_ratings 
                (id, template_id, user_id, rating, review)
                VALUES (?, ?, ?, ?, ?)
            """, (str(uuid.uuid4()), template_id, user_id, rating, review))
            
            # Update template average rating
            cursor = conn.execute("""
                SELECT AVG(rating) as avg_rating, COUNT(*) as count 
                FROM template_ratings WHERE template_id = ?
            """, (template_id,))
            
            result = cursor.fetchone()
            if result:
                conn.execute("""
                    UPDATE rule_templates 
                    SET rating = ?, rating_count = ?, updated_at = ?
                    WHERE id = ?
                """, (result[0], result[1], datetime.now().isoformat(), template_id))
        
        return True
    
    def create_template_package(self, package: TemplatePackage) -> str:
        """Create a template package"""
        import sqlite3
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO template_packages 
                (id, name, description, version, templates, dependencies, installation_script, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                package.id, package.name, package.description, package.version,
                json.dumps(package.templates), json.dumps(package.dependencies or []),
                package.installation_script, json.dumps(package.metadata or {})
            ))
        
        # Store package file
        package_file = self.templates_dir / "packages" / f"{package.id}.yaml"
        with open(package_file, 'w') as f:
            yaml.dump(asdict(package), f, default_flow_style=False)
        
        return package.id
    
    def install_template_package(self, package_id: str, user_id: str) -> bool:
        """Install a template package"""
        package = self.get_template_package(package_id)
        if not package:
            return False
        
        try:
            # Install dependencies first
            if package.dependencies:
                for dep_id in package.dependencies:
                    if not self.install_template_package(dep_id, user_id):
                        logger.warning(f"Failed to install dependency {dep_id}")
            
            # Run installation script if provided
            if package.installation_script:
                exec(package.installation_script)
            
            # Mark templates as installed
            for template_id in package.templates:
                template = self.get_template(template_id)
                if template:
                    self._track_template_usage(template_id, {}, user_id, None, True)
            
            # Store installation in memory
            self.memory_storage.store_memory(
                content=f"Installed template package: {package.name}",
                category="templates",
                metadata={
                    'package_id': package_id,
                    'templates_count': len(package.templates),
                    'user_id': user_id
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to install template package {package_id}: {e}")
            return False
    
    def export_template(self, template_id: str, format: str = "yaml") -> str:
        """Export template in specified format"""
        template = self.get_template(template_id)
        if not template:
            return ""
        
        if format.lower() == "yaml":
            return yaml.dump(asdict(template), default_flow_style=False)
        elif format.lower() == "json":
            return json.dumps(asdict(template), indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def import_template(self, template_data: str, format: str = "yaml", 
                       imported_by: str = "system") -> str:
        """Import template from data"""
        if format.lower() == "yaml":
            data = yaml.safe_load(template_data)
        elif format.lower() == "json":
            data = json.loads(template_data)
        else:
            raise ValueError(f"Unsupported import format: {format}")
        
        # Convert data to RuleTemplate
        template = self._dict_to_template(data)
        template.metadata.status = TemplateStatus.COMMUNITY
        template.metadata.updated_at = datetime.now()
        
        return self.create_template(template)
    
    def _create_authorship_template(self) -> RuleTemplate:
        """Create built-in authorship template"""
        return RuleTemplate(
            metadata=TemplateMetadata(
                id="builtin-authorship",
                name="Authorship Attribution",
                description="Template for setting code and content authorship",
                version="1.0.0",
                author="Lance James",
                organization="Unit 221B Inc",
                category=TemplateCategory.CODING,
                industry=IndustryType.GENERIC,
                status=TemplateStatus.VERIFIED,
                tags=["authorship", "attribution", "coding"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            parameters=[
                TemplateParameter(
                    name="author_name",
                    type="string",
                    description="Name of the author to attribute work to",
                    required=True
                ),
                TemplateParameter(
                    name="organization",
                    type="string", 
                    description="Organization name",
                    required=True
                ),
                TemplateParameter(
                    name="disable_ai_attribution",
                    type="boolean",
                    description="Disable AI attribution in favor of human author",
                    default_value=True
                )
            ],
            template_content={
                "name": "Set Author to {{ author_name }}",
                "description": "Ensure all work is attributed to {{ author_name }}, {{ organization }}",
                "rule_type": "authorship",
                "scope": "{{ scope | default('global') }}",
                "priority": "{{ priority | default('CRITICAL') }}",
                "conditions": [],
                "actions": [
                    {"action_type": "set", "target": "author", "value": "{{ author_name }}"},
                    {"action_type": "set", "target": "organization", "value": "{{ organization }}"},
                    {"action_type": "set", "target": "disable_ai_attribution", "value": "{{ disable_ai_attribution }}"}
                ],
                "tags": ["authorship", "attribution"]
            },
            examples=[
                {
                    "name": "Lance James Attribution",
                    "parameters": {
                        "author_name": "Lance James",
                        "organization": "Unit 221B Inc",
                        "disable_ai_attribution": True
                    }
                }
            ],
            documentation="This template creates authorship rules that ensure all generated code and content is properly attributed to the specified author and organization."
        )
    
    def _create_security_no_secrets_template(self) -> RuleTemplate:
        """Create security no secrets template"""
        return RuleTemplate(
            metadata=TemplateMetadata(
                id="builtin-security-no-secrets",
                name="Security No Secrets Template",
                description="Template for preventing secret exposure",
                version="1.0.0",
                author="Lance James",
                organization="Unit 221B Inc",
                category=TemplateCategory.SECURITY,
                industry=IndustryType.GENERIC,
                status=TemplateStatus.VERIFIED,
                tags=["security", "secrets", "privacy"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            parameters=[
                TemplateParameter(
                    name="scope",
                    type="string",
                    description="Scope to apply secret protection",
                    required=True,
                    default_value="global"
                )
            ],
            template_content={
                "name": "Prevent Secret Exposure in {{ scope }}",
                "description": "Block exposure of secrets, keys, and sensitive data in {{ scope }}",
                "rule_type": "security",
                "scope": "{{ scope }}",
                "priority": "CRITICAL",
                "actions": [
                    {"action_type": "validate", "target": "code_content", "value": "no_secrets"},
                    {"action_type": "block", "target": "secret_exposure", "value": True}
                ],
                "tags": ["security", "secrets", "privacy"]
            },
            documentation="This template creates security rules that prevent exposure of secrets and sensitive data."
        )
    
    def _create_code_quality_template(self) -> RuleTemplate:
        """Create code quality template"""
        return RuleTemplate(
            metadata=TemplateMetadata(
                id="builtin-code-quality",
                name="Code Quality Template",
                description="Template for code quality enforcement",
                version="1.0.0",
                author="Lance James",
                organization="Unit 221B Inc",
                category=TemplateCategory.CODING,
                industry=IndustryType.GENERIC,
                status=TemplateStatus.VERIFIED,
                tags=["code-quality", "standards"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            parameters=[
                TemplateParameter(
                    name="max_complexity",
                    type="integer",
                    description="Maximum cyclomatic complexity",
                    required=True,
                    default_value=10
                )
            ],
            template_content={
                "name": "Code Quality - Max Complexity {{ max_complexity }}",
                "description": "Enforce code quality with maximum complexity of {{ max_complexity }}",
                "rule_type": "coding_style",
                "scope": "global",
                "priority": "HIGH",
                "actions": [
                    {"action_type": "validate", "target": "cyclomatic_complexity", "value": "{{ max_complexity }}"}
                ],
                "tags": ["code-quality", "complexity"]
            },
            documentation="This template creates code quality rules that enforce complexity limits."
        )
    
    def _create_devops_workflow_template(self) -> RuleTemplate:
        """Create DevOps workflow template"""
        return RuleTemplate(
            metadata=TemplateMetadata(
                id="builtin-devops-workflow",
                name="DevOps Workflow Template",
                description="Template for DevOps workflow rules",
                version="1.0.0",
                author="Lance James",
                organization="Unit 221B Inc",
                category=TemplateCategory.DEVOPS,
                industry=IndustryType.TECHNOLOGY,
                status=TemplateStatus.VERIFIED,
                tags=["devops", "workflow"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            parameters=[
                TemplateParameter(
                    name="workflow_type",
                    type="string",
                    description="Type of workflow",
                    required=True,
                    allowed_values=["ci", "cd", "deployment", "testing"]
                )
            ],
            template_content={
                "name": "DevOps {{ workflow_type | title }} Workflow",
                "description": "DevOps workflow rule for {{ workflow_type }}",
                "rule_type": "workflow",
                "scope": "project",
                "priority": "NORMAL",
                "actions": [
                    {"action_type": "set", "target": "workflow_type", "value": "{{ workflow_type }}"}
                ],
                "tags": ["devops", "{{ workflow_type }}"]
            },
            documentation="This template creates DevOps workflow rules."
        )
    
    def _create_security_adaptive_template(self) -> RuleTemplate:
        """Create security adaptive template"""
        return RuleTemplate(
            metadata=TemplateMetadata(
                id="builtin-security-adaptive",
                name="Security Adaptive Template",
                description="Template for adaptive security rules",
                version="1.0.0",
                author="Lance James",
                organization="Unit 221B Inc",
                category=TemplateCategory.SECURITY,
                industry=IndustryType.GENERIC,
                status=TemplateStatus.VERIFIED,
                tags=["security", "adaptive"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            parameters=[
                TemplateParameter(
                    name="threat_threshold",
                    type="string",
                    description="Threat level threshold",
                    required=True,
                    default_value="0.5"
                )
            ],
            template_content={
                "name": "Adaptive Security - Threshold {{ threat_threshold }}",
                "description": "Adaptive security rule with {{ threat_threshold }} threat threshold",
                "rule_type": "security",
                "scope": "global",
                "priority": "CRITICAL",
                "actions": [
                    {"action_type": "set", "target": "threat_threshold", "value": "{{ threat_threshold }}"}
                ],
                "tags": ["security", "adaptive"]
            },
            documentation="This template creates adaptive security rules that respond to threat levels."
        )
    
    def _create_time_based_maintenance_template(self) -> RuleTemplate:
        """Create time-based maintenance template"""
        return RuleTemplate(
            metadata=TemplateMetadata(
                id="builtin-time-based-maintenance",
                name="Time-Based Maintenance Template",
                description="Template for scheduled maintenance rules",
                version="1.0.0",
                author="Lance James",
                organization="Unit 221B Inc",
                category=TemplateCategory.DEVOPS,
                industry=IndustryType.GENERIC,
                status=TemplateStatus.VERIFIED,
                tags=["maintenance", "scheduled"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            parameters=[
                TemplateParameter(
                    name="schedule",
                    type="string",
                    description="Cron schedule expression",
                    required=True,
                    default_value="0 2 * * *"
                )
            ],
            template_content={
                "name": "Scheduled Maintenance - {{ schedule }}",
                "description": "Time-based maintenance rule with schedule {{ schedule }}",
                "rule_type": "operational",
                "scope": "global",
                "priority": "NORMAL",
                "actions": [
                    {"action_type": "set", "target": "maintenance_schedule", "value": "{{ schedule }}"}
                ],
                "tags": ["maintenance", "scheduled"]
            },
            documentation="This template creates time-based maintenance rules."
        )
    
    def _create_context_aware_response_template(self) -> RuleTemplate:
        """Create context-aware response template"""
        return RuleTemplate(
            metadata=TemplateMetadata(
                id="builtin-context-aware-response",
                name="Context-Aware Response Template",
                description="Template for context-aware response rules",
                version="1.0.0",
                author="Lance James",
                organization="Unit 221B Inc",
                category=TemplateCategory.COMMUNICATION,
                industry=IndustryType.GENERIC,
                status=TemplateStatus.VERIFIED,
                tags=["response", "context-aware"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            parameters=[
                TemplateParameter(
                    name="response_style",
                    type="string",
                    description="Response style",
                    required=True,
                    allowed_values=["concise", "detailed", "technical", "friendly"],
                    default_value="concise"
                )
            ],
            template_content={
                "name": "Context-Aware {{ response_style | title }} Response",
                "description": "Context-aware response rule with {{ response_style }} style",
                "rule_type": "communication",
                "scope": "global",
                "priority": "NORMAL",
                "actions": [
                    {"action_type": "set", "target": "response_style", "value": "{{ response_style }}"}
                ],
                "tags": ["response", "{{ response_style }}"]
            },
            documentation="This template creates context-aware response rules."
        )
    
    def _create_gdpr_compliance_template(self) -> RuleTemplate:
        """Create GDPR compliance template"""
        return RuleTemplate(
            metadata=TemplateMetadata(
                id="builtin-gdpr-compliance",
                name="GDPR Compliance Rule",
                description="Template for GDPR data protection compliance",
                version="1.0.0",
                author="Lance James",
                organization="Unit 221B Inc",
                category=TemplateCategory.COMPLIANCE,
                industry=IndustryType.GENERIC,
                status=TemplateStatus.VERIFIED,
                tags=["gdpr", "compliance", "privacy", "data-protection"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            parameters=[
                TemplateParameter(
                    name="control_id",
                    type="string",
                    description="GDPR article or control identifier",
                    required=True
                ),
                TemplateParameter(
                    name="data_types",
                    type="list",
                    description="Types of personal data to protect",
                    required=True
                ),
                TemplateParameter(
                    name="retention_period",
                    type="integer",
                    description="Data retention period in days",
                    default_value=365
                ),
                TemplateParameter(
                    name="consent_required",
                    type="boolean",
                    description="Whether explicit consent is required",
                    default_value=True
                )
            ],
            template_content={
                "name": "GDPR {{ control_id }} Compliance",
                "description": "GDPR compliance rule for {{ control_id }} covering {{ data_types | join(', ') }}",
                "rule_type": "compliance",
                "advanced_type": "compliance",
                "scope": "{{ scope | default('global') }}",
                "priority": "CRITICAL",
                "conditions": [
                    {"field": "data_type", "operator": "in", "value": "{{ data_types }}"}
                ],
                "actions": [
                    {"action_type": "validate", "target": "consent_status", "value": "{{ consent_required }}"},
                    {"action_type": "set", "target": "retention_period", "value": "{{ retention_period }}"},
                    {"action_type": "validate", "target": "data_minimization", "value": True},
                    {"action_type": "block", "target": "unauthorized_processing", "value": True}
                ],
                "compliance_config": {
                    "framework": "gdpr",
                    "control_id": "{{ control_id }}",
                    "severity_level": "critical",
                    "audit_required": True,
                    "documentation_required": True,
                    "evidence_collection": True
                },
                "tags": ["gdpr", "compliance", "privacy"]
            },
            examples=[
                {
                    "name": "GDPR Article 6 Lawful Processing",
                    "parameters": {
                        "control_id": "Article 6",
                        "data_types": ["personal_data", "sensitive_data"],
                        "retention_period": 365,
                        "consent_required": True
                    }
                }
            ],
            documentation="This template creates GDPR compliance rules that ensure personal data processing follows GDPR requirements including consent, data minimization, and retention limits."
        )
    
    def _create_soc2_compliance_template(self) -> RuleTemplate:
        """Create SOC 2 compliance template"""
        return RuleTemplate(
            metadata=TemplateMetadata(
                id="builtin-soc2-compliance",
                name="SOC 2 Compliance Template",
                description="Template for SOC 2 compliance rules",
                version="1.0.0",
                author="Lance James",
                organization="Unit 221B Inc",
                category=TemplateCategory.COMPLIANCE,
                industry=IndustryType.TECHNOLOGY,
                status=TemplateStatus.VERIFIED,
                tags=["soc2", "compliance", "security"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            parameters=[
                TemplateParameter(
                    name="control_id",
                    type="string",
                    description="SOC 2 control identifier",
                    required=True
                ),
                TemplateParameter(
                    name="control_type",
                    type="string",
                    description="Type of SOC 2 control",
                    required=True,
                    allowed_values=["security", "availability", "processing_integrity", "confidentiality", "privacy"]
                )
            ],
            template_content={
                "name": "SOC 2 {{ control_id }} - {{ control_type | title }}",
                "description": "SOC 2 compliance rule for {{ control_id }} ({{ control_type }})",
                "rule_type": "compliance",
                "scope": "global",
                "priority": "CRITICAL",
                "actions": [
                    {"action_type": "validate", "target": "soc2_compliance", "value": "{{ control_id }}"}
                ],
                "tags": ["soc2", "{{ control_type }}", "compliance"]
            },
            documentation="This template creates SOC 2 compliance rules for various control types."
        )
    
    def _create_hipaa_compliance_template(self) -> RuleTemplate:
        """Create HIPAA compliance template"""
        return RuleTemplate(
            metadata=TemplateMetadata(
                id="builtin-hipaa-compliance",
                name="HIPAA Compliance Template",
                description="Template for HIPAA compliance rules",
                version="1.0.0",
                author="Lance James",
                organization="Unit 221B Inc",
                category=TemplateCategory.COMPLIANCE,
                industry=IndustryType.HEALTHCARE,
                status=TemplateStatus.VERIFIED,
                tags=["hipaa", "compliance", "healthcare", "phi"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            parameters=[
                TemplateParameter(
                    name="safeguard_type",
                    type="string",
                    description="Type of HIPAA safeguard",
                    required=True,
                    allowed_values=["administrative", "physical", "technical"]
                ),
                TemplateParameter(
                    name="standard_id",
                    type="string",
                    description="HIPAA standard identifier",
                    required=True
                )
            ],
            template_content={
                "name": "HIPAA {{ standard_id }} - {{ safeguard_type | title }} Safeguard",
                "description": "HIPAA compliance rule for {{ safeguard_type }} safeguard {{ standard_id }}",
                "rule_type": "compliance",
                "scope": "global",
                "priority": "CRITICAL",
                "actions": [
                    {"action_type": "validate", "target": "hipaa_compliance", "value": "{{ standard_id }}"},
                    {"action_type": "validate", "target": "phi_protection", "value": True}
                ],
                "tags": ["hipaa", "{{ safeguard_type }}", "phi", "compliance"]
            },
            documentation="This template creates HIPAA compliance rules for protecting PHI."
        )
    
    def _validate_template(self, template: RuleTemplate) -> Dict[str, Any]:
        """Validate template structure and content"""
        errors = []
        warnings = []
        
        # Validate metadata
        if not template.metadata.id:
            errors.append("Template ID is required")
        
        if not template.metadata.name:
            errors.append("Template name is required")
        
        # Validate version format
        if SEMVER_AVAILABLE:
            try:
                semver.VersionInfo.parse(template.metadata.version)
            except ValueError:
                errors.append(f"Invalid version format: {template.metadata.version}")
        else:
            # Basic version format check
            if not re.match(r'^\d+\.\d+\.\d+', template.metadata.version):
                warnings.append(f"Version format may not be semantic: {template.metadata.version}")
        
        # Validate parameters
        param_names = set()
        for param in template.parameters:
            if param.name in param_names:
                errors.append(f"Duplicate parameter name: {param.name}")
            param_names.add(param.name)
            
            if param.type not in ['string', 'integer', 'boolean', 'list', 'dict']:
                errors.append(f"Invalid parameter type: {param.type}")
        
        # Validate template content
        if not template.template_content:
            errors.append("Template content is required")
        
        # Check for required template fields
        required_fields = ['name', 'description', 'rule_type', 'actions']
        for field in required_fields:
            if field not in template.template_content:
                errors.append(f"Template content missing required field: {field}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def _validate_parameters(self, template: RuleTemplate, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parameters against template definition"""
        errors = []
        warnings = []
        
        # Check required parameters
        for param in template.parameters:
            if param.required and param.name not in parameters:
                errors.append(f"Required parameter missing: {param.name}")
            
            if param.name in parameters:
                value = parameters[param.name]
                
                # Type validation
                if param.type == 'string' and not isinstance(value, str):
                    errors.append(f"Parameter {param.name} must be a string")
                elif param.type == 'integer' and not isinstance(value, int):
                    errors.append(f"Parameter {param.name} must be an integer")
                elif param.type == 'boolean' and not isinstance(value, bool):
                    errors.append(f"Parameter {param.name} must be a boolean")
                elif param.type == 'list' and not isinstance(value, list):
                    errors.append(f"Parameter {param.name} must be a list")
                elif param.type == 'dict' and not isinstance(value, dict):
                    errors.append(f"Parameter {param.name} must be a dict")
                
                # Validation pattern
                if param.validation_pattern and isinstance(value, str):
                    import re
                    if not re.match(param.validation_pattern, value):
                        errors.append(f"Parameter {param.name} does not match pattern: {param.validation_pattern}")
                
                # Allowed values
                if param.allowed_values and value not in param.allowed_values:
                    errors.append(f"Parameter {param.name} must be one of: {param.allowed_values}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def _render_template(self, template: RuleTemplate, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Render template with parameters using Jinja2"""
        # Add default values for missing optional parameters
        render_params = parameters.copy()
        for param in template.parameters:
            if not param.required and param.name not in render_params and param.default_value is not None:
                render_params[param.name] = param.default_value
        
        # Convert template content to JSON string for rendering
        template_str = json.dumps(template.template_content)
        
        if JINJA2_AVAILABLE and self.jinja_env:
            # Render with Jinja2
            jinja_template = self.jinja_env.from_string(template_str)
            rendered_str = jinja_template.render(**render_params)
        else:
            # Simple string replacement fallback
            rendered_str = template_str
            for key, value in render_params.items():
                rendered_str = rendered_str.replace(f"{{{{ {key} }}}}", str(value))
                rendered_str = rendered_str.replace(f"{{{{{key}}}}}", str(value))
        
        # Parse back to dict
        return json.loads(rendered_str)
    
    def _track_template_usage(self, template_id: str, parameters: Dict[str, Any], 
                             user_id: str, rule_id: Optional[str], success: bool, 
                             error_message: str = ""):
        """Track template usage for analytics"""
        import sqlite3
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO template_usage 
                (id, template_id, user_id, machine_id, parameters, created_rule_id, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()), template_id, user_id, 
                getattr(self.memory_storage, 'machine_id', 'unknown'),
                json.dumps(parameters), rule_id, success, error_message
            ))
            
            # Update download count
            conn.execute("""
                UPDATE rule_templates SET download_count = download_count + 1 
                WHERE id = ?
            """, (template_id,))
    
    def _row_to_template(self, row) -> RuleTemplate:
        """Convert database row to RuleTemplate"""
        metadata = TemplateMetadata(
            id=row['id'],
            name=row['name'],
            description=row['description'],
            version=row['version'],
            author=row['author'],
            organization=row['organization'],
            category=TemplateCategory(row['category']),
            industry=IndustryType(row['industry']),
            status=TemplateStatus(row['status']),
            tags=json.loads(row['tags']),
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            download_count=row['download_count'],
            rating=row['rating'],
            rating_count=row['rating_count'],
            license=row['license'],
            dependencies=json.loads(row['dependencies']),
            compatibility=json.loads(row['compatibility'])
        )
        
        parameters = [TemplateParameter(**p) for p in json.loads(row['parameters'])]
        
        return RuleTemplate(
            metadata=metadata,
            parameters=parameters,
            template_content=json.loads(row['template_content']),
            examples=json.loads(row['examples']) if row['examples'] else [],
            documentation=row['documentation'],
            test_cases=json.loads(row['test_cases']) if row['test_cases'] else [],
            validation_schema=json.loads(row['validation_schema']) if row['validation_schema'] else {}
        )