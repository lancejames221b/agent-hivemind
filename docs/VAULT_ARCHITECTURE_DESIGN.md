# Secure Credential Vault Architecture Design

## Overview

The hAIveMind Secure Credential Vault is an enterprise-grade, zero-knowledge credential storage system designed to provide maximum security while maintaining operational efficiency. This document outlines the complete architecture design for Story 8a.

## Table of Contents

1. [Security Architecture](#security-architecture)
2. [Vault Structure](#vault-structure)
3. [Encryption Strategy](#encryption-strategy)
4. [Access Patterns](#access-patterns)
5. [Enterprise Features](#enterprise-features)
6. [hAIveMind Integration](#haivemind-integration)
7. [Database Schema](#database-schema)
8. [API Design](#api-design)
9. [Deployment Architecture](#deployment-architecture)
10. [Security Considerations](#security-considerations)

## Security Architecture

### Core Security Principles

- **Zero-Knowledge Architecture**: Server never sees plaintext passwords or credentials
- **Defense in Depth**: Multiple layers of security controls
- **Principle of Least Privilege**: Minimal access rights by default
- **Cryptographic Excellence**: Industry-standard encryption algorithms
- **Audit Everything**: Comprehensive logging and monitoring

### Encryption Framework

```
┌─────────────────────────────────────────────────────────────┐
│                    Security Framework                        │
├─────────────────────────────────────────────────────────────┤
│  Master Password → Key Derivation (Scrypt/PBKDF2)          │
│                         ↓                                   │
│  Per-Credential Encryption Keys (AES-256-GCM)              │
│                         ↓                                   │
│  Encrypted Storage with Unique Salts & Nonces              │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

1. **Advanced Security Framework** (`security_framework.py`)
   - HSM integration for hardware-backed key storage
   - Multi-level security policies
   - Session management with configurable timeouts
   - Geographic access restrictions

2. **Core Credential Vault** (`core_vault.py`)
   - AES-256-GCM encryption with unique salts/nonces
   - Scrypt/PBKDF2 key derivation
   - SQLite database with encrypted credential storage
   - Comprehensive audit logging

3. **Enterprise Orchestrator** (`enterprise_vault_orchestrator.py`)
   - Coordinates all vault components
   - Real-time monitoring and metrics
   - Background task management
   - Integration with external systems

## Vault Structure

### Hierarchical Organization

```
Organization
├── Projects
│   ├── Environments (dev, staging, prod)
│   │   ├── Services
│   │   │   └── Credentials
│   │   │       ├── Metadata
│   │   │       └── Encrypted Data
│   │   └── Access Controls
│   └── Compliance Labels
└── Global Policies
```

### Credential Types

- **Passwords**: User account passwords
- **API Keys**: Service API authentication keys
- **Certificates**: X.509 certificates and private keys
- **SSH Keys**: SSH public/private key pairs
- **Tokens**: OAuth, JWT, and other authentication tokens
- **Database Connections**: Database connection strings
- **OAuth Credentials**: OAuth client credentials
- **Encryption Keys**: Symmetric encryption keys
- **Signing Keys**: Digital signature keys
- **Webhook Secrets**: Webhook validation secrets

### Metadata Tracking

Each credential includes comprehensive metadata:

```json
{
  "credential_id": "unique_identifier",
  "name": "human_readable_name",
  "description": "detailed_description",
  "credential_type": "password|api_key|certificate|ssh_key|token",
  "environment": "dev|staging|prod",
  "service": "service_name",
  "project": "project_name",
  "owner_id": "user_identifier",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "last_accessed": "2024-01-01T00:00:00Z",
  "expires_at": "2024-12-31T23:59:59Z",
  "rotation_schedule": "0 0 1 * *",
  "status": "active|inactive|expired|compromised|pending_rotation|archived",
  "tags": ["tag1", "tag2"],
  "access_restrictions": {
    "ip_whitelist": ["192.168.1.0/24"],
    "time_restrictions": {"start": "09:00", "end": "17:00"}
  },
  "compliance_labels": ["pci-dss", "soc2", "hipaa"],
  "audit_required": true,
  "emergency_access": false
}
```

## Encryption Strategy

### Master Password Security

1. **Key Derivation**:
   - Primary: Scrypt (N=16384, r=8, p=1)
   - Fallback: PBKDF2 (100,000 iterations)
   - Salt: 32 bytes cryptographically secure random

2. **Password Requirements**:
   - Minimum 12 characters
   - Mixed case, numbers, special characters
   - No dictionary words or common patterns
   - Regular rotation enforcement

### Per-Credential Encryption

```python
# Encryption Process
salt = secrets.token_bytes(32)          # Unique salt per credential
nonce = secrets.token_bytes(12)         # GCM nonce
key = derive_key(master_password, salt) # Scrypt key derivation
cipher = AES-256-GCM(key, nonce)       # Authenticated encryption
encrypted_data = cipher.encrypt(credential_json)
tag = cipher.tag                        # Authentication tag
```

### Key Management

- **Key Versioning**: Support for key rotation without data migration
- **HSM Integration**: Hardware Security Module support for enterprise deployments
- **Key Escrow**: Secure key backup for business continuity
- **Zero-Knowledge**: Server never stores or logs plaintext keys

## Access Patterns

### Role-Based Access Control (RBAC)

| Role | Permissions | Description |
|------|-------------|-------------|
| **Viewer** | Read | Can view credential metadata and decrypt credentials |
| **Operator** | Read, Write | Can view, create, and update credentials |
| **Admin** | Read, Write, Grant Access | Can manage credentials and grant access to others |
| **Owner** | Full Control | Complete control over owned credentials |
| **Emergency** | Override Access | Emergency access with enhanced logging |

### Access Control Matrix

```
┌─────────────┬─────────┬─────────┬─────────┬─────────┬───────────┐
│ Operation   │ Viewer  │ Operator│ Admin   │ Owner   │ Emergency │
├─────────────┼─────────┼─────────┼─────────┼─────────┼───────────┤
│ View        │    ✓    │    ✓    │    ✓    │    ✓    │     ✓     │
│ Create      │    ✗    │    ✓    │    ✓    │    ✓    │     ✓     │
│ Update      │    ✗    │    ✓    │    ✓    │    ✓    │     ✓     │
│ Delete      │    ✗    │    ✗    │    ✗    │    ✓    │     ✓     │
│ Grant Access│    ✗    │    ✗    │    ✓    │    ✓    │     ✓     │
│ Emergency   │    ✗    │    ✗    │    ✗    │    ✗    │     ✓     │
└─────────────┴─────────┴─────────┴─────────┴─────────┴───────────┘
```

### Authentication Mechanisms

1. **Multi-Factor Authentication (MFA)**
   - TOTP (Time-based One-Time Password)
   - Hardware tokens (YubiKey, etc.)
   - Biometric authentication
   - SMS/Email verification (backup only)

2. **Session Management**
   - JWT-based session tokens
   - Configurable session timeouts
   - Concurrent session limits
   - IP-based restrictions

3. **API Access**
   - API key authentication
   - OAuth 2.0 / OpenID Connect
   - Certificate-based authentication
   - Service account tokens

## Enterprise Features

### Compliance Framework

#### SOC 2 Compliance
- **Security**: Access controls, encryption, vulnerability management
- **Availability**: High availability, disaster recovery, monitoring
- **Processing Integrity**: Data validation, error handling, logging
- **Confidentiality**: Data classification, access restrictions
- **Privacy**: Data retention, user consent, data portability

#### HIPAA Compliance
- **Administrative Safeguards**: Security officer, workforce training
- **Physical Safeguards**: Facility access, workstation security
- **Technical Safeguards**: Access control, audit controls, integrity, transmission security

#### PCI DSS Compliance
- **Build and Maintain Secure Networks**: Firewall configuration, default passwords
- **Protect Cardholder Data**: Data protection, encryption
- **Maintain Vulnerability Management**: Antivirus, secure systems
- **Implement Strong Access Control**: Access restrictions, unique IDs, physical access
- **Regularly Monitor and Test Networks**: Logging, security testing
- **Maintain Information Security Policy**: Security policy, risk assessment

### Enterprise Integration

#### Directory Services
- **LDAP Integration**: User authentication and group management
- **Active Directory**: Windows domain integration
- **SAML 2.0**: Single sign-on with enterprise identity providers
- **OAuth 2.0**: Integration with cloud identity providers

#### Monitoring and Alerting
- **Prometheus Metrics**: Performance and security metrics
- **Grafana Dashboards**: Real-time monitoring dashboards
- **SIEM Integration**: Security Information and Event Management
- **Alerting**: Email, Slack, PagerDuty integration

#### Backup and Recovery
- **Automated Backups**: Scheduled encrypted backups
- **Multi-Location Storage**: Local and cloud backup storage
- **Point-in-Time Recovery**: Granular recovery capabilities
- **Disaster Recovery**: RTO/RPO targets and procedures

## hAIveMind Integration

### Security Analytics

The vault integrates deeply with the hAIveMind system to provide:

1. **Access Pattern Analysis**
   - Behavioral analytics for anomaly detection
   - Risk scoring based on access patterns
   - Automated threat detection and response

2. **Threat Intelligence Sharing**
   - Cross-system threat correlation
   - Collaborative incident response
   - Threat intelligence feeds integration

3. **Operational Intelligence**
   - Usage pattern optimization
   - Performance monitoring and tuning
   - Capacity planning and scaling

### Memory Categories

The vault stores operational data in hAIveMind memory categories:

- `vault_operations`: Operational events and metrics
- `security_events`: Security-related events and alerts
- `access_patterns`: User access patterns and analytics
- `threat_intelligence`: Security threat data and indicators
- `compliance_events`: Compliance-related events and reports

### Collaborative Features

1. **Distributed Threat Detection**
   - Multi-node threat correlation
   - Shared threat intelligence
   - Coordinated incident response

2. **Best Practice Sharing**
   - Security configuration recommendations
   - Operational efficiency insights
   - Compliance guidance

3. **Automated Responses**
   - Threat-based credential rotation
   - Automated access revocation
   - Emergency response coordination

## Database Schema

### Core Tables

#### credential_metadata
```sql
CREATE TABLE credential_metadata (
    credential_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    credential_type TEXT NOT NULL,
    environment TEXT NOT NULL,
    service TEXT NOT NULL,
    project TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    last_accessed TIMESTAMP,
    expires_at TIMESTAMP,
    rotation_schedule TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    tags TEXT,
    access_restrictions TEXT,
    compliance_labels TEXT,
    audit_required BOOLEAN DEFAULT FALSE,
    emergency_access BOOLEAN DEFAULT FALSE
);
```

#### encrypted_credentials
```sql
CREATE TABLE encrypted_credentials (
    credential_id TEXT PRIMARY KEY,
    encrypted_data BLOB NOT NULL,
    encryption_algorithm TEXT NOT NULL,
    key_derivation_method TEXT NOT NULL,
    salt BLOB NOT NULL,
    nonce BLOB NOT NULL,
    tag BLOB NOT NULL,
    key_version INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    FOREIGN KEY (credential_id) REFERENCES credential_metadata (credential_id)
);
```

#### vault_access
```sql
CREATE TABLE vault_access (
    access_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    credential_id TEXT NOT NULL,
    access_level TEXT NOT NULL,
    granted_by TEXT NOT NULL,
    granted_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP,
    ip_restrictions TEXT,
    time_restrictions TEXT,
    purpose TEXT,
    FOREIGN KEY (credential_id) REFERENCES credential_metadata (credential_id)
);
```

#### vault_audit_log
```sql
CREATE TABLE vault_audit_log (
    audit_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    credential_id TEXT,
    action TEXT NOT NULL,
    details TEXT,
    ip_address TEXT,
    user_agent TEXT,
    timestamp TIMESTAMP NOT NULL,
    success BOOLEAN NOT NULL
);
```

## API Design

### REST API Endpoints

#### Credential Management
- `POST /api/v1/credentials` - Create new credential
- `GET /api/v1/credentials` - List accessible credentials
- `GET /api/v1/credentials/{id}` - Retrieve specific credential
- `PUT /api/v1/credentials/{id}` - Update credential
- `DELETE /api/v1/credentials/{id}` - Delete credential

#### Access Management
- `POST /api/v1/credentials/{id}/access` - Grant access
- `DELETE /api/v1/credentials/{id}/access/{user_id}` - Revoke access
- `GET /api/v1/credentials/{id}/access` - List access grants

#### Vault Operations
- `GET /api/v1/vault/status` - Vault status and health
- `GET /api/v1/vault/statistics` - Usage statistics
- `POST /api/v1/vault/emergency/revoke` - Emergency credential revocation

#### Security Operations
- `POST /api/v1/security/sessions` - Create security session
- `GET /api/v1/security/threats` - Threat summary
- `POST /api/v1/security/response` - Initiate threat response

### Authentication

All API endpoints require authentication via:
- JWT Bearer tokens
- API keys with proper scoping
- Certificate-based authentication (for services)

## Deployment Architecture

### High Availability Setup

```
┌─────────────────────────────────────────────────────────────┐
│                    Load Balancer                            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Vault API  │  │  Vault API  │  │  Vault API  │        │
│  │   Node 1    │  │   Node 2    │  │   Node 3    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Redis     │  │   Redis     │  │   Redis     │        │
│  │  Primary    │  │  Replica    │  │  Replica    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐                          │
│  │  Database   │  │  Database   │                          │
│  │  Primary    │  │  Replica    │                          │
│  └─────────────┘  └─────────────┘                          │
└─────────────────────────────────────────────────────────────┘
```

### Security Zones

1. **DMZ Zone**: Load balancers and reverse proxies
2. **Application Zone**: Vault API servers
3. **Data Zone**: Databases and encrypted storage
4. **Management Zone**: Monitoring and administration

### Network Security

- TLS 1.3 for all communications
- Network segmentation with VLANs
- Firewall rules with least privilege
- VPN access for administrative functions

## Security Considerations

### Threat Model

#### Assets
- Master passwords and derived keys
- Encrypted credential data
- Access control policies
- Audit logs and metadata

#### Threats
- **External Attackers**: Network-based attacks, credential theft
- **Malicious Insiders**: Privilege abuse, data exfiltration
- **System Compromise**: Server compromise, malware
- **Physical Access**: Hardware theft, console access

#### Mitigations
- **Encryption**: AES-256-GCM with secure key derivation
- **Access Controls**: RBAC with principle of least privilege
- **Monitoring**: Comprehensive audit logging and alerting
- **Network Security**: TLS, VPNs, network segmentation
- **Physical Security**: Secure data centers, hardware security

### Security Best Practices

1. **Key Management**
   - Hardware Security Modules (HSMs) for key storage
   - Regular key rotation with automated procedures
   - Secure key backup and recovery procedures

2. **Access Control**
   - Multi-factor authentication for all users
   - Regular access reviews and certification
   - Automated access provisioning and deprovisioning

3. **Monitoring and Alerting**
   - Real-time security monitoring
   - Automated threat detection and response
   - Regular security assessments and penetration testing

4. **Data Protection**
   - Encryption at rest and in transit
   - Data classification and handling procedures
   - Secure data destruction and disposal

### Compliance Considerations

#### Data Residency
- Geographic data storage restrictions
- Cross-border data transfer controls
- Sovereignty and jurisdiction requirements

#### Audit Requirements
- Comprehensive audit trails
- Tamper-evident logging
- Regular compliance assessments

#### Privacy Protection
- Data minimization principles
- User consent and control
- Right to erasure and portability

## Conclusion

The hAIveMind Secure Credential Vault provides enterprise-grade security for credential storage and management while maintaining operational efficiency and compliance requirements. The architecture is designed to scale from small teams to large enterprises while providing the flexibility to integrate with existing security infrastructure.

The zero-knowledge design ensures that even with full system compromise, credential data remains protected. The integration with the hAIveMind system provides advanced analytics and collaborative security capabilities that enhance the overall security posture.

This design serves as the foundation for implementing Stories 8b through 8e, providing the secure infrastructure needed for advanced vault features like automated rotation, compliance reporting, and threat detection.