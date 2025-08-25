#!/usr/bin/env python3
"""
Compliance Rule Templates for hAIveMind Rules Engine
Provides comprehensive compliance framework templates (GDPR, SOC 2, HIPAA, etc.)

Author: Lance James, Unit 221B Inc
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass, asdict
import logging

from rule_template_system import RuleTemplate, TemplateMetadata, TemplateParameter, TemplateCategory, IndustryType, TemplateStatus
from advanced_rule_types import ComplianceFramework

logger = logging.getLogger(__name__)

class ComplianceTemplateLibrary:
    """Library of compliance rule templates for various frameworks"""
    
    def __init__(self):
        self.templates = {}
        self._initialize_templates()
    
    def _initialize_templates(self):
        """Initialize all compliance templates"""
        # GDPR Templates
        self.templates.update(self._create_gdpr_templates())
        
        # SOC 2 Templates
        self.templates.update(self._create_soc2_templates())
        
        # HIPAA Templates
        self.templates.update(self._create_hipaa_templates())
        
        # PCI DSS Templates
        self.templates.update(self._create_pci_dss_templates())
        
        # ISO 27001 Templates
        self.templates.update(self._create_iso27001_templates())
        
        # NIST Templates
        self.templates.update(self._create_nist_templates())
    
    def get_template(self, template_id: str) -> Optional[RuleTemplate]:
        """Get compliance template by ID"""
        return self.templates.get(template_id)
    
    def get_templates_by_framework(self, framework: ComplianceFramework) -> List[RuleTemplate]:
        """Get all templates for a specific compliance framework"""
        return [template for template in self.templates.values() 
                if framework.value in template.metadata.tags]
    
    def get_all_templates(self) -> List[RuleTemplate]:
        """Get all compliance templates"""
        return list(self.templates.values())
    
    def _create_gdpr_templates(self) -> Dict[str, RuleTemplate]:
        """Create GDPR compliance templates"""
        templates = {}
        
        # GDPR Article 6 - Lawful Processing
        templates["gdpr-article-6-lawful-processing"] = RuleTemplate(
            metadata=TemplateMetadata(
                id="gdpr-article-6-lawful-processing",
                name="GDPR Article 6 - Lawful Processing",
                description="Ensures lawful basis for personal data processing",
                version="1.0.0",
                author="Lance James",
                organization="Unit 221B Inc",
                category=TemplateCategory.COMPLIANCE,
                industry=IndustryType.GENERIC,
                status=TemplateStatus.VERIFIED,
                tags=["gdpr", "compliance", "privacy", "article-6", "lawful-processing"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            parameters=[
                TemplateParameter(
                    name="lawful_basis",
                    type="string",
                    description="Lawful basis for processing",
                    required=True,
                    allowed_values=["consent", "contract", "legal_obligation", "vital_interests", "public_task", "legitimate_interests"]
                ),
                TemplateParameter(
                    name="data_categories",
                    type="list",
                    description="Categories of personal data being processed",
                    required=True
                ),
                TemplateParameter(
                    name="processing_purposes",
                    type="list",
                    description="Purposes for data processing",
                    required=True
                ),
                TemplateParameter(
                    name="consent_mechanism",
                    type="string",
                    description="How consent is obtained (if applicable)",
                    required=False
                )
            ],
            template_content={
                "name": "GDPR Article 6 - {{ lawful_basis | title }} Processing",
                "description": "Ensures lawful processing of {{ data_categories | join(', ') }} for {{ processing_purposes | join(', ') }}",
                "rule_type": "compliance",
                "advanced_type": "compliance",
                "scope": "global",
                "priority": "CRITICAL",
                "conditions": [
                    {"field": "data_category", "operator": "in", "value": "{{ data_categories }}"},
                    {"field": "processing_purpose", "operator": "in", "value": "{{ processing_purposes }}"}
                ],
                "actions": [
                    {"action_type": "validate", "target": "lawful_basis", "value": "{{ lawful_basis }}"},
                    {"action_type": "validate", "target": "consent_status", "value": "{% if lawful_basis == 'consent' %}required{% else %}not_required{% endif %}"},
                    {"action_type": "set", "target": "processing_lawful", "value": True},
                    {"action_type": "block", "target": "unlawful_processing", "value": True}
                ],
                "compliance_config": {
                    "framework": "gdpr",
                    "control_id": "Article 6",
                    "severity_level": "critical",
                    "audit_required": True,
                    "documentation_required": True,
                    "evidence_collection": True,
                    "remediation_actions": ["stop_processing", "obtain_consent", "document_lawful_basis"]
                },
                "tags": ["gdpr", "article-6", "lawful-processing"]
            },
            examples=[
                {
                    "name": "Marketing Consent Processing",
                    "parameters": {
                        "lawful_basis": "consent",
                        "data_categories": ["email", "name", "preferences"],
                        "processing_purposes": ["marketing", "newsletters"],
                        "consent_mechanism": "opt-in checkbox"
                    }
                }
            ],
            documentation="This template ensures compliance with GDPR Article 6 by validating lawful basis for personal data processing."
        )
        
        # GDPR Article 7 - Consent
        templates["gdpr-article-7-consent"] = RuleTemplate(
            metadata=TemplateMetadata(
                id="gdpr-article-7-consent",
                name="GDPR Article 7 - Consent Management",
                description="Manages consent requirements and withdrawal rights",
                version="1.0.0",
                author="Lance James",
                organization="Unit 221B Inc",
                category=TemplateCategory.COMPLIANCE,
                industry=IndustryType.GENERIC,
                status=TemplateStatus.VERIFIED,
                tags=["gdpr", "compliance", "consent", "article-7"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            parameters=[
                TemplateParameter(
                    name="consent_type",
                    type="string",
                    description="Type of consent required",
                    required=True,
                    allowed_values=["explicit", "implicit", "opt-in", "opt-out"]
                ),
                TemplateParameter(
                    name="withdrawal_mechanism",
                    type="string",
                    description="How users can withdraw consent",
                    required=True
                ),
                TemplateParameter(
                    name="consent_granularity",
                    type="string",
                    description="Level of consent granularity",
                    required=False,
                    allowed_values=["purpose-specific", "category-specific", "global"],
                    default_value="purpose-specific"
                )
            ],
            template_content={
                "name": "GDPR Article 7 - {{ consent_type | title }} Consent",
                "description": "Manages {{ consent_type }} consent with {{ consent_granularity }} granularity",
                "rule_type": "compliance",
                "advanced_type": "compliance",
                "scope": "global",
                "priority": "CRITICAL",
                "conditions": [
                    {"field": "requires_consent", "operator": "eq", "value": True}
                ],
                "actions": [
                    {"action_type": "validate", "target": "consent_obtained", "value": True},
                    {"action_type": "validate", "target": "consent_type", "value": "{{ consent_type }}"},
                    {"action_type": "set", "target": "withdrawal_available", "value": True},
                    {"action_type": "set", "target": "withdrawal_mechanism", "value": "{{ withdrawal_mechanism }}"},
                    {"action_type": "validate", "target": "consent_granularity", "value": "{{ consent_granularity }}"},
                    {"action_type": "block", "target": "processing_without_consent", "value": True}
                ],
                "compliance_config": {
                    "framework": "gdpr",
                    "control_id": "Article 7",
                    "severity_level": "critical",
                    "audit_required": True,
                    "documentation_required": True,
                    "evidence_collection": True,
                    "remediation_actions": ["obtain_consent", "stop_processing", "implement_withdrawal"]
                },
                "tags": ["gdpr", "article-7", "consent"]
            }
        )
        
        # GDPR Article 17 - Right to Erasure
        templates["gdpr-article-17-erasure"] = RuleTemplate(
            metadata=TemplateMetadata(
                id="gdpr-article-17-erasure",
                name="GDPR Article 17 - Right to Erasure",
                description="Implements right to erasure (right to be forgotten)",
                version="1.0.0",
                author="Lance James",
                organization="Unit 221B Inc",
                category=TemplateCategory.COMPLIANCE,
                industry=IndustryType.GENERIC,
                status=TemplateStatus.VERIFIED,
                tags=["gdpr", "compliance", "erasure", "article-17", "right-to-be-forgotten"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            parameters=[
                TemplateParameter(
                    name="erasure_timeframe",
                    type="integer",
                    description="Maximum days to complete erasure",
                    required=True,
                    default_value=30
                ),
                TemplateParameter(
                    name="erasure_scope",
                    type="list",
                    description="Systems/databases to erase from",
                    required=True
                ),
                TemplateParameter(
                    name="exceptions",
                    type="list",
                    description="Legal exceptions to erasure",
                    required=False,
                    default_value=[]
                )
            ],
            template_content={
                "name": "GDPR Article 17 - Right to Erasure",
                "description": "Implements right to erasure within {{ erasure_timeframe }} days across {{ erasure_scope | join(', ') }}",
                "rule_type": "compliance",
                "advanced_type": "compliance",
                "scope": "global",
                "priority": "CRITICAL",
                "conditions": [
                    {"field": "erasure_request", "operator": "eq", "value": True}
                ],
                "actions": [
                    {"action_type": "validate", "target": "erasure_grounds", "value": "valid"},
                    {"action_type": "set", "target": "erasure_timeframe", "value": "{{ erasure_timeframe }}"},
                    {"action_type": "invoke", "target": "erasure_process", "value": "{{ erasure_scope }}"},
                    {"action_type": "validate", "target": "legal_exceptions", "value": "{{ exceptions }}"},
                    {"action_type": "set", "target": "erasure_confirmation", "value": True}
                ],
                "compliance_config": {
                    "framework": "gdpr",
                    "control_id": "Article 17",
                    "severity_level": "critical",
                    "audit_required": True,
                    "documentation_required": True,
                    "evidence_collection": True,
                    "remediation_actions": ["complete_erasure", "document_exceptions", "notify_data_subject"]
                },
                "tags": ["gdpr", "article-17", "erasure", "right-to-be-forgotten"]
            }
        )
        
        return templates
    
    def _create_soc2_templates(self) -> Dict[str, RuleTemplate]:
        """Create SOC 2 compliance templates"""
        templates = {}
        
        # SOC 2 Security - Access Controls
        templates["soc2-security-access-controls"] = RuleTemplate(
            metadata=TemplateMetadata(
                id="soc2-security-access-controls",
                name="SOC 2 Security - Access Controls",
                description="Implements SOC 2 access control requirements",
                version="1.0.0",
                author="Lance James",
                organization="Unit 221B Inc",
                category=TemplateCategory.COMPLIANCE,
                industry=IndustryType.TECHNOLOGY,
                status=TemplateStatus.VERIFIED,
                tags=["soc2", "compliance", "security", "access-controls"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            parameters=[
                TemplateParameter(
                    name="access_levels",
                    type="list",
                    description="Defined access levels",
                    required=True
                ),
                TemplateParameter(
                    name="authentication_method",
                    type="string",
                    description="Required authentication method",
                    required=True,
                    allowed_values=["mfa", "sso", "certificate", "biometric"]
                ),
                TemplateParameter(
                    name="review_frequency",
                    type="integer",
                    description="Access review frequency in days",
                    required=True,
                    default_value=90
                )
            ],
            template_content={
                "name": "SOC 2 Security - {{ authentication_method | upper }} Access Controls",
                "description": "Enforces SOC 2 access controls with {{ authentication_method }} authentication",
                "rule_type": "compliance",
                "advanced_type": "security_adaptive",
                "scope": "global",
                "priority": "CRITICAL",
                "conditions": [
                    {"field": "access_request", "operator": "eq", "value": True}
                ],
                "actions": [
                    {"action_type": "validate", "target": "authentication_method", "value": "{{ authentication_method }}"},
                    {"action_type": "validate", "target": "access_level", "value": "{{ access_levels }}"},
                    {"action_type": "set", "target": "access_review_required", "value": True},
                    {"action_type": "set", "target": "review_frequency", "value": "{{ review_frequency }}"},
                    {"action_type": "block", "target": "unauthorized_access", "value": True}
                ],
                "compliance_config": {
                    "framework": "soc2",
                    "control_id": "CC6.1",
                    "severity_level": "critical",
                    "audit_required": True,
                    "documentation_required": True,
                    "evidence_collection": True,
                    "remediation_actions": ["revoke_access", "enable_mfa", "conduct_review"]
                },
                "security_config": {
                    "threat_level_threshold": 0.3,
                    "adaptive_response": True,
                    "escalation_rules": ["security-incident-response"],
                    "threat_indicators": ["failed_authentication", "unusual_access_patterns"],
                    "response_actions": {
                        "low": ["log_event"],
                        "medium": ["require_additional_auth"],
                        "high": ["block_access", "alert_security"],
                        "critical": ["lock_account", "immediate_review"]
                    }
                },
                "tags": ["soc2", "security", "access-controls"]
            }
        )
        
        # SOC 2 Availability - System Monitoring
        templates["soc2-availability-monitoring"] = RuleTemplate(
            metadata=TemplateMetadata(
                id="soc2-availability-monitoring",
                name="SOC 2 Availability - System Monitoring",
                description="Implements SOC 2 system availability monitoring",
                version="1.0.0",
                author="Lance James",
                organization="Unit 221B Inc",
                category=TemplateCategory.COMPLIANCE,
                industry=IndustryType.TECHNOLOGY,
                status=TemplateStatus.VERIFIED,
                tags=["soc2", "compliance", "availability", "monitoring"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            parameters=[
                TemplateParameter(
                    name="uptime_target",
                    type="string",
                    description="Target uptime percentage",
                    required=True,
                    default_value="99.9%"
                ),
                TemplateParameter(
                    name="monitoring_interval",
                    type="integer",
                    description="Monitoring check interval in seconds",
                    required=True,
                    default_value=60
                ),
                TemplateParameter(
                    name="alert_thresholds",
                    type="dict",
                    description="Alert thresholds for various metrics",
                    required=True
                )
            ],
            template_content={
                "name": "SOC 2 Availability - {{ uptime_target }} Uptime Monitoring",
                "description": "Monitors system availability with {{ uptime_target }} target uptime",
                "rule_type": "compliance",
                "advanced_type": "performance_based",
                "scope": "global",
                "priority": "HIGH",
                "conditions": [
                    {"field": "system_monitoring", "operator": "eq", "value": True}
                ],
                "actions": [
                    {"action_type": "set", "target": "uptime_target", "value": "{{ uptime_target }}"},
                    {"action_type": "set", "target": "monitoring_interval", "value": "{{ monitoring_interval }}"},
                    {"action_type": "validate", "target": "alert_thresholds", "value": "{{ alert_thresholds }}"},
                    {"action_type": "invoke", "target": "availability_monitoring", "value": True}
                ],
                "compliance_config": {
                    "framework": "soc2",
                    "control_id": "A1.1",
                    "severity_level": "high",
                    "audit_required": True,
                    "documentation_required": True,
                    "evidence_collection": True,
                    "remediation_actions": ["investigate_downtime", "implement_redundancy", "update_procedures"]
                },
                "performance_thresholds": "{{ alert_thresholds }}",
                "tags": ["soc2", "availability", "monitoring"]
            }
        )
        
        return templates
    
    def _create_hipaa_templates(self) -> Dict[str, RuleTemplate]:
        """Create HIPAA compliance templates"""
        templates = {}
        
        # HIPAA Security Rule - Access Control
        templates["hipaa-security-access-control"] = RuleTemplate(
            metadata=TemplateMetadata(
                id="hipaa-security-access-control",
                name="HIPAA Security Rule - Access Control",
                description="Implements HIPAA access control requirements for PHI",
                version="1.0.0",
                author="Lance James",
                organization="Unit 221B Inc",
                category=TemplateCategory.COMPLIANCE,
                industry=IndustryType.HEALTHCARE,
                status=TemplateStatus.VERIFIED,
                tags=["hipaa", "compliance", "security", "phi", "access-control"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            parameters=[
                TemplateParameter(
                    name="phi_categories",
                    type="list",
                    description="Categories of PHI being protected",
                    required=True
                ),
                TemplateParameter(
                    name="minimum_necessary",
                    type="boolean",
                    description="Enforce minimum necessary standard",
                    required=True,
                    default_value=True
                ),
                TemplateParameter(
                    name="role_based_access",
                    type="boolean",
                    description="Use role-based access controls",
                    required=True,
                    default_value=True
                )
            ],
            template_content={
                "name": "HIPAA Security - PHI Access Control",
                "description": "Controls access to {{ phi_categories | join(', ') }} with minimum necessary enforcement",
                "rule_type": "compliance",
                "advanced_type": "security_adaptive",
                "scope": "global",
                "priority": "CRITICAL",
                "conditions": [
                    {"field": "data_type", "operator": "in", "value": "{{ phi_categories }}"}
                ],
                "actions": [
                    {"action_type": "validate", "target": "authorized_user", "value": True},
                    {"action_type": "validate", "target": "minimum_necessary", "value": "{{ minimum_necessary }}"},
                    {"action_type": "validate", "target": "role_authorization", "value": "{{ role_based_access }}"},
                    {"action_type": "set", "target": "audit_logging", "value": True},
                    {"action_type": "block", "target": "unauthorized_phi_access", "value": True}
                ],
                "compliance_config": {
                    "framework": "hipaa",
                    "control_id": "164.312(a)(1)",
                    "severity_level": "critical",
                    "audit_required": True,
                    "documentation_required": True,
                    "evidence_collection": True,
                    "remediation_actions": ["revoke_access", "conduct_risk_assessment", "update_policies"]
                },
                "security_config": {
                    "threat_level_threshold": 0.2,
                    "adaptive_response": True,
                    "escalation_rules": ["hipaa-breach-response"],
                    "threat_indicators": ["unauthorized_access_attempt", "phi_exposure_risk"],
                    "response_actions": {
                        "low": ["log_access", "notify_supervisor"],
                        "medium": ["require_justification", "additional_authentication"],
                        "high": ["block_access", "security_review"],
                        "critical": ["immediate_lockout", "breach_assessment"]
                    }
                },
                "tags": ["hipaa", "security", "phi", "access-control"]
            }
        )
        
        # HIPAA Breach Notification
        templates["hipaa-breach-notification"] = RuleTemplate(
            metadata=TemplateMetadata(
                id="hipaa-breach-notification",
                name="HIPAA Breach Notification Rule",
                description="Implements HIPAA breach notification requirements",
                version="1.0.0",
                author="Lance James",
                organization="Unit 221B Inc",
                category=TemplateCategory.COMPLIANCE,
                industry=IndustryType.HEALTHCARE,
                status=TemplateStatus.VERIFIED,
                tags=["hipaa", "compliance", "breach", "notification"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            parameters=[
                TemplateParameter(
                    name="notification_timeframes",
                    type="dict",
                    description="Notification timeframes for different parties",
                    required=True,
                    default_value={
                        "individuals": 60,
                        "hhs": 60,
                        "media": 60
                    }
                ),
                TemplateParameter(
                    name="breach_threshold",
                    type="integer",
                    description="Number of individuals affected to trigger notification",
                    required=True,
                    default_value=500
                )
            ],
            template_content={
                "name": "HIPAA Breach Notification",
                "description": "Manages HIPAA breach notifications with {{ notification_timeframes }} day timeframes",
                "rule_type": "compliance",
                "advanced_type": "workflow_triggered",
                "scope": "global",
                "priority": "CRITICAL",
                "conditions": [
                    {"field": "security_incident", "operator": "eq", "value": True},
                    {"field": "phi_involved", "operator": "eq", "value": True}
                ],
                "actions": [
                    {"action_type": "validate", "target": "breach_assessment", "value": "required"},
                    {"action_type": "set", "target": "notification_timeframes", "value": "{{ notification_timeframes }}"},
                    {"action_type": "conditional_set", "target": "media_notification", 
                     "value": "{% if breach_threshold >= 500 %}required{% else %}not_required{% endif %}"},
                    {"action_type": "invoke", "target": "breach_notification_process", "value": True}
                ],
                "compliance_config": {
                    "framework": "hipaa",
                    "control_id": "164.404",
                    "severity_level": "critical",
                    "audit_required": True,
                    "documentation_required": True,
                    "evidence_collection": True,
                    "remediation_actions": ["assess_breach", "notify_affected", "report_hhs", "update_safeguards"]
                },
                "tags": ["hipaa", "breach", "notification"]
            }
        )
        
        return templates
    
    def _create_pci_dss_templates(self) -> Dict[str, RuleTemplate]:
        """Create PCI DSS compliance templates"""
        templates = {}
        
        # PCI DSS Requirement 3 - Protect Cardholder Data
        templates["pci-dss-req3-protect-cardholder-data"] = RuleTemplate(
            metadata=TemplateMetadata(
                id="pci-dss-req3-protect-cardholder-data",
                name="PCI DSS Requirement 3 - Protect Cardholder Data",
                description="Implements PCI DSS cardholder data protection requirements",
                version="1.0.0",
                author="Lance James",
                organization="Unit 221B Inc",
                category=TemplateCategory.COMPLIANCE,
                industry=IndustryType.FINANCE,
                status=TemplateStatus.VERIFIED,
                tags=["pci-dss", "compliance", "cardholder-data", "encryption"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            parameters=[
                TemplateParameter(
                    name="encryption_standard",
                    type="string",
                    description="Encryption standard to use",
                    required=True,
                    allowed_values=["AES-256", "AES-128", "3DES"],
                    default_value="AES-256"
                ),
                TemplateParameter(
                    name="data_retention_period",
                    type="integer",
                    description="Maximum data retention period in days",
                    required=True,
                    default_value=365
                ),
                TemplateParameter(
                    name="masking_requirements",
                    type="dict",
                    description="Data masking requirements",
                    required=True
                )
            ],
            template_content={
                "name": "PCI DSS Req 3 - {{ encryption_standard }} Cardholder Data Protection",
                "description": "Protects cardholder data using {{ encryption_standard }} encryption",
                "rule_type": "compliance",
                "advanced_type": "security_adaptive",
                "scope": "global",
                "priority": "CRITICAL",
                "conditions": [
                    {"field": "data_type", "operator": "in", "value": ["pan", "cardholder_data", "sensitive_auth_data"]}
                ],
                "actions": [
                    {"action_type": "validate", "target": "encryption_at_rest", "value": "{{ encryption_standard }}"},
                    {"action_type": "validate", "target": "encryption_in_transit", "value": "required"},
                    {"action_type": "set", "target": "data_retention_limit", "value": "{{ data_retention_period }}"},
                    {"action_type": "validate", "target": "data_masking", "value": "{{ masking_requirements }}"},
                    {"action_type": "block", "target": "unencrypted_cardholder_data", "value": True}
                ],
                "compliance_config": {
                    "framework": "pci_dss",
                    "control_id": "3.4",
                    "severity_level": "critical",
                    "audit_required": True,
                    "documentation_required": True,
                    "evidence_collection": True,
                    "remediation_actions": ["encrypt_data", "implement_masking", "secure_deletion"]
                },
                "tags": ["pci-dss", "cardholder-data", "encryption"]
            }
        )
        
        return templates
    
    def _create_iso27001_templates(self) -> Dict[str, RuleTemplate]:
        """Create ISO 27001 compliance templates"""
        templates = {}
        
        # ISO 27001 A.9.1.1 - Access Control Policy
        templates["iso27001-a911-access-control-policy"] = RuleTemplate(
            metadata=TemplateMetadata(
                id="iso27001-a911-access-control-policy",
                name="ISO 27001 A.9.1.1 - Access Control Policy",
                description="Implements ISO 27001 access control policy requirements",
                version="1.0.0",
                author="Lance James",
                organization="Unit 221B Inc",
                category=TemplateCategory.COMPLIANCE,
                industry=IndustryType.GENERIC,
                status=TemplateStatus.VERIFIED,
                tags=["iso27001", "compliance", "access-control", "policy"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            parameters=[
                TemplateParameter(
                    name="access_control_objectives",
                    type="list",
                    description="Access control objectives",
                    required=True
                ),
                TemplateParameter(
                    name="policy_review_frequency",
                    type="integer",
                    description="Policy review frequency in months",
                    required=True,
                    default_value=12
                )
            ],
            template_content={
                "name": "ISO 27001 A.9.1.1 - Access Control Policy",
                "description": "Enforces access control policy with {{ policy_review_frequency }} month review cycle",
                "rule_type": "compliance",
                "advanced_type": "time_based",
                "scope": "global",
                "priority": "HIGH",
                "conditions": [
                    {"field": "access_request", "operator": "eq", "value": True}
                ],
                "actions": [
                    {"action_type": "validate", "target": "access_control_objectives", "value": "{{ access_control_objectives }}"},
                    {"action_type": "set", "target": "policy_review_required", "value": True},
                    {"action_type": "set", "target": "review_frequency", "value": "{{ policy_review_frequency }}"}
                ],
                "schedule": {
                    "cron_expression": "0 0 1 */{{ policy_review_frequency }} *",
                    "timezone": "UTC"
                },
                "compliance_config": {
                    "framework": "iso27001",
                    "control_id": "A.9.1.1",
                    "severity_level": "high",
                    "audit_required": True,
                    "documentation_required": True,
                    "evidence_collection": True,
                    "remediation_actions": ["update_policy", "conduct_review", "train_staff"]
                },
                "tags": ["iso27001", "access-control", "policy"]
            }
        )
        
        return templates
    
    def _create_nist_templates(self) -> Dict[str, RuleTemplate]:
        """Create NIST compliance templates"""
        templates = {}
        
        # NIST 800-53 AC-2 - Account Management
        templates["nist-800-53-ac2-account-management"] = RuleTemplate(
            metadata=TemplateMetadata(
                id="nist-800-53-ac2-account-management",
                name="NIST 800-53 AC-2 - Account Management",
                description="Implements NIST 800-53 account management controls",
                version="1.0.0",
                author="Lance James",
                organization="Unit 221B Inc",
                category=TemplateCategory.COMPLIANCE,
                industry=IndustryType.GOVERNMENT,
                status=TemplateStatus.VERIFIED,
                tags=["nist", "compliance", "account-management", "800-53"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            parameters=[
                TemplateParameter(
                    name="account_types",
                    type="list",
                    description="Types of accounts to manage",
                    required=True
                ),
                TemplateParameter(
                    name="approval_workflow",
                    type="boolean",
                    description="Require approval workflow for account creation",
                    required=True,
                    default_value=True
                ),
                TemplateParameter(
                    name="periodic_review_interval",
                    type="integer",
                    description="Account review interval in days",
                    required=True,
                    default_value=90
                )
            ],
            template_content={
                "name": "NIST 800-53 AC-2 - Account Management",
                "description": "Manages {{ account_types | join(', ') }} accounts with {{ periodic_review_interval }} day review cycle",
                "rule_type": "compliance",
                "advanced_type": "workflow_triggered",
                "scope": "global",
                "priority": "HIGH",
                "conditions": [
                    {"field": "account_operation", "operator": "in", "value": ["create", "modify", "disable", "remove"]}
                ],
                "actions": [
                    {"action_type": "validate", "target": "account_type", "value": "{{ account_types }}"},
                    {"action_type": "conditional_set", "target": "approval_required", 
                     "value": "{% if approval_workflow %}true{% else %}false{% endif %}"},
                    {"action_type": "set", "target": "review_interval", "value": "{{ periodic_review_interval }}"},
                    {"action_type": "invoke", "target": "account_management_process", "value": True}
                ],
                "compliance_config": {
                    "framework": "nist",
                    "control_id": "AC-2",
                    "severity_level": "high",
                    "audit_required": True,
                    "documentation_required": True,
                    "evidence_collection": True,
                    "remediation_actions": ["review_accounts", "update_procedures", "disable_unused_accounts"]
                },
                "tags": ["nist", "800-53", "account-management"]
            }
        )
        
        return templates