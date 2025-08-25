#!/usr/bin/env python3
"""
Specialized Rule Categories for hAIveMind Rules Engine
Implements specialized rule categories for authorship, code quality, security, etc.

Author: Lance James, Unit 221B Inc
"""

import json
import uuid
import re
import ast
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
import logging
from pathlib import Path

from rules_engine import Rule, RuleCondition, RuleAction, RuleType, RuleScope, RulePriority, RuleStatus
from advanced_rule_types import AdvancedRule, AdvancedRuleType

logger = logging.getLogger(__name__)

class SpecializedRuleCategory(Enum):
    """Specialized rule categories"""
    AUTHORSHIP_ATTRIBUTION = "authorship_attribution"
    CODE_QUALITY_ENFORCEMENT = "code_quality_enforcement"
    SECURITY_POSTURE = "security_posture"
    RESPONSE_PATTERNS = "response_patterns"
    ERROR_HANDLING = "error_handling"
    DOCUMENTATION_CONTROL = "documentation_control"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    ACCESSIBILITY_COMPLIANCE = "accessibility_compliance"
    TESTING_REQUIREMENTS = "testing_requirements"
    DEPLOYMENT_GOVERNANCE = "deployment_governance"

class CodeQualityMetric(Enum):
    """Code quality metrics to enforce"""
    CYCLOMATIC_COMPLEXITY = "cyclomatic_complexity"
    LINE_LENGTH = "line_length"
    FUNCTION_LENGTH = "function_length"
    NESTING_DEPTH = "nesting_depth"
    DUPLICATION = "duplication"
    NAMING_CONVENTIONS = "naming_conventions"
    COMMENT_DENSITY = "comment_density"
    TEST_COVERAGE = "test_coverage"

class SecurityThreatLevel(Enum):
    """Security threat levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class AuthorshipConfig:
    """Authorship attribution configuration"""
    default_author: str
    organization: str
    copyright_template: str
    license_header: str
    disable_ai_attribution: bool = True
    require_author_comments: bool = False
    author_email: Optional[str] = None
    attribution_format: str = "header"

@dataclass
class CodeQualityConfig:
    """Code quality enforcement configuration"""
    max_complexity: int = 10
    max_line_length: int = 120
    max_function_length: int = 50
    max_nesting_depth: int = 4
    min_test_coverage: float = 0.8
    enforce_naming_conventions: bool = True
    require_docstrings: bool = False
    allow_todo_comments: bool = True
    max_todo_age_days: int = 30

@dataclass
class SecurityPostureConfig:
    """Security posture configuration"""
    threat_level_threshold: float = 0.5
    require_input_validation: bool = True
    block_dangerous_functions: List[str] = None
    require_authentication: bool = True
    enforce_https: bool = True
    scan_for_vulnerabilities: bool = True
    security_headers_required: List[str] = None

@dataclass
class ResponsePatternConfig:
    """Response pattern configuration"""
    max_response_length: int = 1000
    preferred_tone: str = "professional"
    avoid_phrases: List[str] = None
    required_disclaimers: List[str] = None
    response_template: Optional[str] = None
    include_confidence_scores: bool = False

class SpecializedRuleFactory:
    """Factory for creating specialized rule categories"""
    
    def __init__(self, memory_storage):
        self.memory_storage = memory_storage
    
    def create_authorship_rules(self, config: AuthorshipConfig) -> List[AdvancedRule]:
        """Create authorship attribution rules"""
        rules = []
        
        # Main authorship attribution rule
        authorship_rule = AdvancedRule(
            id=f"authorship-{str(uuid.uuid4())[:8]}",
            name="Code Authorship Attribution",
            description=f"Ensures all code is attributed to {config.default_author}, {config.organization}",
            rule_type=RuleType.AUTHORSHIP,
            advanced_type=AdvancedRuleType.CONTEXT_AWARE,
            scope=RuleScope.GLOBAL,
            priority=RulePriority.CRITICAL,
            status=RuleStatus.ACTIVE,
            conditions=[
                RuleCondition(
                    field="task_type",
                    operator="in",
                    value=["code_generation", "file_creation", "documentation"]
                )
            ],
            actions=[
                RuleAction(
                    action_type="set",
                    target="author",
                    value=config.default_author
                ),
                RuleAction(
                    action_type="set",
                    target="organization",
                    value=config.organization
                ),
                RuleAction(
                    action_type="set",
                    target="disable_ai_attribution",
                    value=config.disable_ai_attribution
                ),
                RuleAction(
                    action_type="transform",
                    target="file_header",
                    value=config.copyright_template,
                    parameters={"template_vars": {"author": config.default_author, "organization": config.organization}}
                )
            ],
            tags=["authorship", "attribution", "copyright"],
            created_at=datetime.now(),
            created_by="system",
            updated_at=datetime.now(),
            updated_by="system",
            metadata={
                "category": SpecializedRuleCategory.AUTHORSHIP_ATTRIBUTION.value,
                "config": asdict(config)
            }
        )
        rules.append(authorship_rule)
        
        # License header enforcement rule
        if config.license_header:
            license_rule = AdvancedRule(
                id=f"license-{str(uuid.uuid4())[:8]}",
                name="License Header Enforcement",
                description="Ensures proper license headers in all source files",
                rule_type=RuleType.AUTHORSHIP,
                advanced_type=AdvancedRuleType.CONDITIONAL,
                scope=RuleScope.GLOBAL,
                priority=RulePriority.HIGH,
                status=RuleStatus.ACTIVE,
                conditions=[
                    RuleCondition(
                        field="file_type",
                        operator="in",
                        value=["py", "js", "ts", "java", "cpp", "c", "h"]
                    )
                ],
                actions=[
                    RuleAction(
                        action_type="validate",
                        target="license_header",
                        value=config.license_header
                    ),
                    RuleAction(
                        action_type="transform",
                        target="file_content",
                        value="prepend_license",
                        parameters={"license_text": config.license_header}
                    )
                ],
                tags=["license", "legal", "header"],
                created_at=datetime.now(),
                created_by="system",
                updated_at=datetime.now(),
                updated_by="system",
                metadata={
                    "category": SpecializedRuleCategory.AUTHORSHIP_ATTRIBUTION.value,
                    "license_header": config.license_header
                }
            )
            rules.append(license_rule)
        
        return rules
    
    def create_code_quality_rules(self, config: CodeQualityConfig) -> List[AdvancedRule]:
        """Create code quality enforcement rules"""
        rules = []
        
        # Complexity enforcement rule
        complexity_rule = AdvancedRule(
            id=f"complexity-{str(uuid.uuid4())[:8]}",
            name="Cyclomatic Complexity Control",
            description=f"Enforces maximum cyclomatic complexity of {config.max_complexity}",
            rule_type=RuleType.CODING_STYLE,
            advanced_type=AdvancedRuleType.PERFORMANCE_BASED,
            scope=RuleScope.GLOBAL,
            priority=RulePriority.HIGH,
            status=RuleStatus.ACTIVE,
            conditions=[
                RuleCondition(
                    field="task_type",
                    operator="eq",
                    value="code_generation"
                )
            ],
            actions=[
                RuleAction(
                    action_type="validate",
                    target="cyclomatic_complexity",
                    value=config.max_complexity,
                    parameters={"metric": "max_complexity"}
                ),
                RuleAction(
                    action_type="block",
                    target="high_complexity_code",
                    value=True,
                    parameters={"threshold": config.max_complexity}
                )
            ],
            tags=["code-quality", "complexity", "maintainability"],
            created_at=datetime.now(),
            created_by="system",
            updated_at=datetime.now(),
            updated_by="system",
            performance_thresholds={
                "max_complexity": config.max_complexity,
                "warning_threshold": config.max_complexity * 0.8
            },
            metadata={
                "category": SpecializedRuleCategory.CODE_QUALITY_ENFORCEMENT.value,
                "config": asdict(config)
            }
        )
        rules.append(complexity_rule)
        
        # Line length enforcement rule
        line_length_rule = AdvancedRule(
            id=f"line-length-{str(uuid.uuid4())[:8]}",
            name="Line Length Enforcement",
            description=f"Enforces maximum line length of {config.max_line_length} characters",
            rule_type=RuleType.CODING_STYLE,
            advanced_type=AdvancedRuleType.CONDITIONAL,
            scope=RuleScope.GLOBAL,
            priority=RulePriority.NORMAL,
            status=RuleStatus.ACTIVE,
            conditions=[
                RuleCondition(
                    field="task_type",
                    operator="eq",
                    value="code_generation"
                )
            ],
            actions=[
                RuleAction(
                    action_type="validate",
                    target="line_length",
                    value=config.max_line_length,
                    parameters={"metric": "max_line_length"}
                ),
                RuleAction(
                    action_type="transform",
                    target="code_formatting",
                    value="wrap_long_lines",
                    parameters={"max_length": config.max_line_length}
                )
            ],
            tags=["code-quality", "formatting", "readability"],
            created_at=datetime.now(),
            created_by="system",
            updated_at=datetime.now(),
            updated_by="system",
            metadata={
                "category": SpecializedRuleCategory.CODE_QUALITY_ENFORCEMENT.value,
                "max_line_length": config.max_line_length
            }
        )
        rules.append(line_length_rule)
        
        # Test coverage rule
        if config.min_test_coverage > 0:
            test_coverage_rule = AdvancedRule(
                id=f"test-coverage-{str(uuid.uuid4())[:8]}",
                name="Test Coverage Requirement",
                description=f"Requires minimum test coverage of {config.min_test_coverage * 100}%",
                rule_type=RuleType.CODING_STYLE,
                advanced_type=AdvancedRuleType.PERFORMANCE_BASED,
                scope=RuleScope.PROJECT,
                priority=RulePriority.HIGH,
                status=RuleStatus.ACTIVE,
                conditions=[
                    RuleCondition(
                        field="task_type",
                        operator="in",
                        value=["code_generation", "test_creation"]
                    )
                ],
                actions=[
                    RuleAction(
                        action_type="validate",
                        target="test_coverage",
                        value=config.min_test_coverage,
                        parameters={"metric": "coverage_percentage"}
                    ),
                    RuleAction(
                        action_type="invoke",
                        target="generate_tests",
                        value=True,
                        parameters={"coverage_target": config.min_test_coverage}
                    )
                ],
                tags=["testing", "coverage", "quality"],
                created_at=datetime.now(),
                created_by="system",
                updated_at=datetime.now(),
                updated_by="system",
                performance_thresholds={
                    "min_coverage": config.min_test_coverage,
                    "target_coverage": min(config.min_test_coverage + 0.1, 1.0)
                },
                metadata={
                    "category": SpecializedRuleCategory.TESTING_REQUIREMENTS.value,
                    "min_coverage": config.min_test_coverage
                }
            )
            rules.append(test_coverage_rule)
        
        return rules
    
    def create_security_posture_rules(self, config: SecurityPostureConfig) -> List[AdvancedRule]:
        """Create security posture rules"""
        rules = []
        
        # Input validation rule
        if config.require_input_validation:
            input_validation_rule = AdvancedRule(
                id=f"input-validation-{str(uuid.uuid4())[:8]}",
                name="Input Validation Enforcement",
                description="Requires proper input validation for all user inputs",
                rule_type=RuleType.SECURITY,
                advanced_type=AdvancedRuleType.SECURITY_ADAPTIVE,
                scope=RuleScope.GLOBAL,
                priority=RulePriority.CRITICAL,
                status=RuleStatus.ACTIVE,
                conditions=[
                    RuleCondition(
                        field="task_type",
                        operator="eq",
                        value="code_generation"
                    ),
                    RuleCondition(
                        field="involves_user_input",
                        operator="eq",
                        value=True
                    )
                ],
                actions=[
                    RuleAction(
                        action_type="validate",
                        target="input_validation",
                        value="required",
                        parameters={"validation_types": ["sanitization", "type_checking", "bounds_checking"]}
                    ),
                    RuleAction(
                        action_type="block",
                        target="unvalidated_input",
                        value=True
                    )
                ],
                tags=["security", "input-validation", "sanitization"],
                created_at=datetime.now(),
                created_by="system",
                updated_at=datetime.now(),
                updated_by="system",
                security_config={
                    "threat_level_threshold": config.threat_level_threshold,
                    "adaptive_response": True,
                    "threat_indicators": ["sql_injection", "xss", "command_injection"],
                    "response_actions": {
                        "low": ["log_warning"],
                        "medium": ["require_validation"],
                        "high": ["block_execution", "alert_security"],
                        "critical": ["immediate_block", "security_review"]
                    }
                },
                metadata={
                    "category": SpecializedRuleCategory.SECURITY_POSTURE.value,
                    "config": asdict(config)
                }
            )
            rules.append(input_validation_rule)
        
        # Dangerous functions blocking rule
        if config.block_dangerous_functions:
            dangerous_functions_rule = AdvancedRule(
                id=f"dangerous-functions-{str(uuid.uuid4())[:8]}",
                name="Dangerous Functions Blocking",
                description="Blocks usage of dangerous or deprecated functions",
                rule_type=RuleType.SECURITY,
                advanced_type=AdvancedRuleType.SECURITY_ADAPTIVE,
                scope=RuleScope.GLOBAL,
                priority=RulePriority.CRITICAL,
                status=RuleStatus.ACTIVE,
                conditions=[
                    RuleCondition(
                        field="task_type",
                        operator="eq",
                        value="code_generation"
                    )
                ],
                actions=[
                    RuleAction(
                        action_type="validate",
                        target="function_usage",
                        value="safe_functions_only",
                        parameters={"blocked_functions": config.block_dangerous_functions}
                    ),
                    RuleAction(
                        action_type="block",
                        target="dangerous_function_usage",
                        value=True,
                        parameters={"functions": config.block_dangerous_functions}
                    )
                ],
                tags=["security", "dangerous-functions", "code-safety"],
                created_at=datetime.now(),
                created_by="system",
                updated_at=datetime.now(),
                updated_by="system",
                security_config={
                    "threat_level_threshold": 0.1,  # Very low threshold for dangerous functions
                    "adaptive_response": True,
                    "threat_indicators": config.block_dangerous_functions,
                    "response_actions": {
                        "low": ["suggest_alternative"],
                        "medium": ["require_justification"],
                        "high": ["block_usage"],
                        "critical": ["immediate_block", "security_alert"]
                    }
                },
                metadata={
                    "category": SpecializedRuleCategory.SECURITY_POSTURE.value,
                    "blocked_functions": config.block_dangerous_functions
                }
            )
            rules.append(dangerous_functions_rule)
        
        # HTTPS enforcement rule
        if config.enforce_https:
            https_rule = AdvancedRule(
                id=f"https-enforcement-{str(uuid.uuid4())[:8]}",
                name="HTTPS Enforcement",
                description="Requires HTTPS for all network communications",
                rule_type=RuleType.SECURITY,
                advanced_type=AdvancedRuleType.CONDITIONAL,
                scope=RuleScope.GLOBAL,
                priority=RulePriority.HIGH,
                status=RuleStatus.ACTIVE,
                conditions=[
                    RuleCondition(
                        field="involves_network",
                        operator="eq",
                        value=True
                    )
                ],
                actions=[
                    RuleAction(
                        action_type="validate",
                        target="protocol",
                        value="https",
                        parameters={"allowed_protocols": ["https", "wss"]}
                    ),
                    RuleAction(
                        action_type="block",
                        target="insecure_protocols",
                        value=True,
                        parameters={"blocked_protocols": ["http", "ws", "ftp", "telnet"]}
                    )
                ],
                tags=["security", "https", "encryption"],
                created_at=datetime.now(),
                created_by="system",
                updated_at=datetime.now(),
                updated_by="system",
                metadata={
                    "category": SpecializedRuleCategory.SECURITY_POSTURE.value,
                    "enforce_https": True
                }
            )
            rules.append(https_rule)
        
        return rules
    
    def create_response_pattern_rules(self, config: ResponsePatternConfig) -> List[AdvancedRule]:
        """Create response pattern rules"""
        rules = []
        
        # Response length control rule
        length_control_rule = AdvancedRule(
            id=f"response-length-{str(uuid.uuid4())[:8]}",
            name="Response Length Control",
            description=f"Limits response length to {config.max_response_length} characters",
            rule_type=RuleType.COMMUNICATION,
            advanced_type=AdvancedRuleType.CONDITIONAL,
            scope=RuleScope.GLOBAL,
            priority=RulePriority.NORMAL,
            status=RuleStatus.ACTIVE,
            conditions=[
                RuleCondition(
                    field="task_type",
                    operator="in",
                    value=["response_generation", "explanation", "documentation"]
                )
            ],
            actions=[
                RuleAction(
                    action_type="validate",
                    target="response_length",
                    value=config.max_response_length,
                    parameters={"unit": "characters"}
                ),
                RuleAction(
                    action_type="transform",
                    target="response_content",
                    value="truncate_if_needed",
                    parameters={"max_length": config.max_response_length}
                )
            ],
            tags=["communication", "response-length", "brevity"],
            created_at=datetime.now(),
            created_by="system",
            updated_at=datetime.now(),
            updated_by="system",
            metadata={
                "category": SpecializedRuleCategory.RESPONSE_PATTERNS.value,
                "config": asdict(config)
            }
        )
        rules.append(length_control_rule)
        
        # Tone enforcement rule
        tone_rule = AdvancedRule(
            id=f"tone-control-{str(uuid.uuid4())[:8]}",
            name="Response Tone Control",
            description=f"Enforces {config.preferred_tone} tone in responses",
            rule_type=RuleType.COMMUNICATION,
            advanced_type=AdvancedRuleType.CONTEXT_AWARE,
            scope=RuleScope.GLOBAL,
            priority=RulePriority.NORMAL,
            status=RuleStatus.ACTIVE,
            conditions=[
                RuleCondition(
                    field="task_type",
                    operator="in",
                    value=["response_generation", "explanation", "communication"]
                )
            ],
            actions=[
                RuleAction(
                    action_type="set",
                    target="response_tone",
                    value=config.preferred_tone
                ),
                RuleAction(
                    action_type="validate",
                    target="tone_consistency",
                    value="required",
                    parameters={"target_tone": config.preferred_tone}
                )
            ],
            tags=["communication", "tone", "style"],
            created_at=datetime.now(),
            created_by="system",
            updated_at=datetime.now(),
            updated_by="system",
            context_adaptation={
                "adaptation_fields": ["user_preference", "conversation_context"],
                "learning_enabled": True,
                "adaptation_threshold": 0.7,
                "historical_window": 86400
            },
            metadata={
                "category": SpecializedRuleCategory.RESPONSE_PATTERNS.value,
                "preferred_tone": config.preferred_tone
            }
        )
        rules.append(tone_rule)
        
        # Phrase avoidance rule
        if config.avoid_phrases:
            phrase_avoidance_rule = AdvancedRule(
                id=f"phrase-avoidance-{str(uuid.uuid4())[:8]}",
                name="Phrase Avoidance Control",
                description="Prevents usage of specified phrases in responses",
                rule_type=RuleType.COMMUNICATION,
                advanced_type=AdvancedRuleType.CONDITIONAL,
                scope=RuleScope.GLOBAL,
                priority=RulePriority.HIGH,
                status=RuleStatus.ACTIVE,
                conditions=[
                    RuleCondition(
                        field="task_type",
                        operator="in",
                        value=["response_generation", "communication"]
                    )
                ],
                actions=[
                    RuleAction(
                        action_type="validate",
                        target="phrase_usage",
                        value="avoid_specified",
                        parameters={"avoided_phrases": config.avoid_phrases}
                    ),
                    RuleAction(
                        action_type="transform",
                        target="response_content",
                        value="replace_phrases",
                        parameters={"phrases_to_replace": config.avoid_phrases}
                    )
                ],
                tags=["communication", "phrase-control", "content-filtering"],
                created_at=datetime.now(),
                created_by="system",
                updated_at=datetime.now(),
                updated_by="system",
                metadata={
                    "category": SpecializedRuleCategory.RESPONSE_PATTERNS.value,
                    "avoid_phrases": config.avoid_phrases
                }
            )
            rules.append(phrase_avoidance_rule)
        
        return rules
    
    def create_error_handling_rules(self) -> List[AdvancedRule]:
        """Create error handling rules"""
        rules = []
        
        # Fallback options rule
        fallback_rule = AdvancedRule(
            id=f"fallback-{str(uuid.uuid4())[:8]}",
            name="Error Fallback Options",
            description="Always provide fallback options and retry logic for errors",
            rule_type=RuleType.OPERATIONAL,
            advanced_type=AdvancedRuleType.CONDITIONAL,
            scope=RuleScope.GLOBAL,
            priority=RulePriority.HIGH,
            status=RuleStatus.ACTIVE,
            conditions=[
                RuleCondition(
                    field="error_occurred",
                    operator="eq",
                    value=True
                )
            ],
            actions=[
                RuleAction(
                    action_type="set",
                    target="provide_fallback",
                    value=True
                ),
                RuleAction(
                    action_type="set",
                    target="include_retry_logic",
                    value=True
                ),
                RuleAction(
                    action_type="invoke",
                    target="generate_alternatives",
                    value=True,
                    parameters={"min_alternatives": 2}
                )
            ],
            tags=["error-handling", "fallback", "resilience"],
            created_at=datetime.now(),
            created_by="system",
            updated_at=datetime.now(),
            updated_by="system",
            metadata={
                "category": SpecializedRuleCategory.ERROR_HANDLING.value
            }
        )
        rules.append(fallback_rule)
        
        # Graceful degradation rule
        degradation_rule = AdvancedRule(
            id=f"degradation-{str(uuid.uuid4())[:8]}",
            name="Graceful Degradation",
            description="Implement graceful degradation when full functionality is unavailable",
            rule_type=RuleType.OPERATIONAL,
            advanced_type=AdvancedRuleType.PERFORMANCE_BASED,
            scope=RuleScope.GLOBAL,
            priority=RulePriority.HIGH,
            status=RuleStatus.ACTIVE,
            conditions=[
                RuleCondition(
                    field="system_performance",
                    operator="regex",
                    value="degraded|limited|reduced"
                )
            ],
            actions=[
                RuleAction(
                    action_type="set",
                    target="enable_degraded_mode",
                    value=True
                ),
                RuleAction(
                    action_type="transform",
                    target="functionality",
                    value="reduce_to_core_features",
                    parameters={"priority_features": ["basic_response", "error_handling"]}
                )
            ],
            tags=["error-handling", "degradation", "performance"],
            created_at=datetime.now(),
            created_by="system",
            updated_at=datetime.now(),
            updated_by="system",
            performance_thresholds={
                "response_time_threshold": 5000,  # 5 seconds
                "error_rate_threshold": 0.1,     # 10%
                "availability_threshold": 0.95   # 95%
            },
            metadata={
                "category": SpecializedRuleCategory.ERROR_HANDLING.value
            }
        )
        rules.append(degradation_rule)
        
        return rules
    
    def create_documentation_control_rules(self) -> List[AdvancedRule]:
        """Create documentation control rules"""
        rules = []
        
        # No documentation creation rule
        no_docs_rule = AdvancedRule(
            id=f"no-docs-{str(uuid.uuid4())[:8]}",
            name="Documentation Creation Control",
            description="Never create documentation files unless explicitly requested",
            rule_type=RuleType.WORKFLOW,
            advanced_type=AdvancedRuleType.CONDITIONAL,
            scope=RuleScope.GLOBAL,
            priority=RulePriority.HIGH,
            status=RuleStatus.ACTIVE,
            conditions=[
                RuleCondition(
                    field="task_type",
                    operator="in",
                    value=["file_creation", "documentation_generation"]
                ),
                RuleCondition(
                    field="file_type",
                    operator="in",
                    value=["md", "rst", "txt", "doc", "docx"]
                )
            ],
            actions=[
                RuleAction(
                    action_type="validate",
                    target="explicit_documentation_request",
                    value="required",
                    parameters={"validation_type": "user_explicit_request"}
                ),
                RuleAction(
                    action_type="block",
                    target="unsolicited_documentation",
                    value=True,
                    parameters={"blocked_extensions": ["md", "rst", "txt"]}
                )
            ],
            tags=["documentation", "file-creation", "workflow"],
            created_at=datetime.now(),
            created_by="system",
            updated_at=datetime.now(),
            updated_by="system",
            metadata={
                "category": SpecializedRuleCategory.DOCUMENTATION_CONTROL.value
            }
        )
        rules.append(no_docs_rule)
        
        # README prevention rule
        readme_rule = AdvancedRule(
            id=f"no-readme-{str(uuid.uuid4())[:8]}",
            name="README File Prevention",
            description="Never proactively create README files unless explicitly requested",
            rule_type=RuleType.WORKFLOW,
            advanced_type=AdvancedRuleType.CONDITIONAL,
            scope=RuleScope.GLOBAL,
            priority=RulePriority.HIGH,
            status=RuleStatus.ACTIVE,
            conditions=[
                RuleCondition(
                    field="filename",
                    operator="regex",
                    value="(?i)readme.*"
                )
            ],
            actions=[
                RuleAction(
                    action_type="validate",
                    target="explicit_readme_request",
                    value="required"
                ),
                RuleAction(
                    action_type="block",
                    target="automatic_readme_creation",
                    value=True
                )
            ],
            tags=["readme", "documentation", "prevention"],
            created_at=datetime.now(),
            created_by="system",
            updated_at=datetime.now(),
            updated_by="system",
            metadata={
                "category": SpecializedRuleCategory.DOCUMENTATION_CONTROL.value
            }
        )
        rules.append(readme_rule)
        
        return rules


class SpecializedRuleManager:
    """Manager for specialized rule categories"""
    
    def __init__(self, memory_storage, rules_engine):
        self.memory_storage = memory_storage
        self.rules_engine = rules_engine
        self.factory = SpecializedRuleFactory(memory_storage)
    
    def deploy_lance_james_rules(self) -> List[str]:
        """Deploy Lance James specific rule set"""
        deployed_rules = []
        
        # Authorship rules
        authorship_config = AuthorshipConfig(
            default_author="Lance James",
            organization="Unit 221B Inc",
            copyright_template="# Author: Lance James, Unit 221B Inc\n# Copyright (c) {year} Unit 221B Inc. All rights reserved.",
            license_header="# Licensed under MIT License",
            disable_ai_attribution=True,
            author_email="lance@unit221b.com"
        )
        
        authorship_rules = self.factory.create_authorship_rules(authorship_config)
        for rule in authorship_rules:
            rule_id = self.rules_engine.db.create_rule(rule)
            deployed_rules.append(rule_id)
        
        # Code quality rules
        code_quality_config = CodeQualityConfig(
            max_complexity=10,
            max_line_length=120,
            max_function_length=50,
            max_nesting_depth=4,
            min_test_coverage=0.8,
            enforce_naming_conventions=True,
            require_docstrings=False,  # Lance prefers minimal comments
            allow_todo_comments=True,
            max_todo_age_days=30
        )
        
        quality_rules = self.factory.create_code_quality_rules(code_quality_config)
        for rule in quality_rules:
            rule_id = self.rules_engine.db.create_rule(rule)
            deployed_rules.append(rule_id)
        
        # Security posture rules
        security_config = SecurityPostureConfig(
            threat_level_threshold=0.3,
            require_input_validation=True,
            block_dangerous_functions=["eval", "exec", "system", "shell_exec", "passthru"],
            require_authentication=True,
            enforce_https=True,
            scan_for_vulnerabilities=True,
            security_headers_required=["X-Content-Type-Options", "X-Frame-Options", "X-XSS-Protection"]
        )
        
        security_rules = self.factory.create_security_posture_rules(security_config)
        for rule in security_rules:
            rule_id = self.rules_engine.db.create_rule(rule)
            deployed_rules.append(rule_id)
        
        # Response pattern rules
        response_config = ResponsePatternConfig(
            max_response_length=1000,
            preferred_tone="professional",
            avoid_phrases=["I'm sorry", "I apologize", "I can't help", "I don't know"],
            required_disclaimers=[],
            include_confidence_scores=False
        )
        
        response_rules = self.factory.create_response_pattern_rules(response_config)
        for rule in response_rules:
            rule_id = self.rules_engine.db.create_rule(rule)
            deployed_rules.append(rule_id)
        
        # Error handling rules
        error_rules = self.factory.create_error_handling_rules()
        for rule in error_rules:
            rule_id = self.rules_engine.db.create_rule(rule)
            deployed_rules.append(rule_id)
        
        # Documentation control rules
        doc_rules = self.factory.create_documentation_control_rules()
        for rule in doc_rules:
            rule_id = self.rules_engine.db.create_rule(rule)
            deployed_rules.append(rule_id)
        
        # Store deployment in hAIveMind memory
        self.memory_storage.store_memory(
            content=f"Deployed Lance James specialized rule set: {len(deployed_rules)} rules",
            category="rules",
            metadata={
                "deployment_type": "lance_james_rules",
                "rules_deployed": deployed_rules,
                "categories": [
                    "authorship_attribution",
                    "code_quality_enforcement", 
                    "security_posture",
                    "response_patterns",
                    "error_handling",
                    "documentation_control"
                ]
            }
        )
        
        return deployed_rules
    
    def get_specialized_rules_by_category(self, category: SpecializedRuleCategory) -> List[Rule]:
        """Get all rules for a specialized category"""
        # Query rules with matching category metadata
        all_rules = self.rules_engine.db.get_applicable_rules({})
        
        specialized_rules = []
        for rule in all_rules:
            if (rule.metadata and 
                rule.metadata.get("category") == category.value):
                specialized_rules.append(rule)
        
        return specialized_rules
    
    def update_specialized_config(self, category: SpecializedRuleCategory, 
                                 config: Dict[str, Any]) -> bool:
        """Update configuration for a specialized rule category"""
        rules = self.get_specialized_rules_by_category(category)
        
        for rule in rules:
            # Update rule metadata with new config
            if not rule.metadata:
                rule.metadata = {}
            rule.metadata["config"] = config
            rule.updated_at = datetime.now()
            rule.updated_by = "system"
            
            # Update rule in database
            self.rules_engine.db.update_rule(rule, f"Updated {category.value} configuration")
        
        # Store update in memory
        self.memory_storage.store_memory(
            content=f"Updated {category.value} configuration",
            category="rules",
            metadata={
                "category": category.value,
                "config_update": config,
                "rules_affected": len(rules)
            }
        )
        
        return True