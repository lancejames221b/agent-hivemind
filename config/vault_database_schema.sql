-- Enterprise Credential Vault Database Schema
-- Author: Lance James, Unit 221B
-- Date: 2025-08-25
-- Version: 1.0

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create custom types
CREATE TYPE credential_type AS ENUM (
    'password',
    'api_key', 
    'certificate',
    'ssh_key',
    'oauth_token',
    'database',
    'cloud_key',
    'custom'
);

CREATE TYPE environment_type AS ENUM (
    'production',
    'staging', 
    'development',
    'test',
    'sandbox'
);

CREATE TYPE risk_level AS ENUM (
    'low',
    'medium',
    'high', 
    'critical'
);

CREATE TYPE user_role AS ENUM (
    'super_admin',
    'organization_admin',
    'environment_admin', 
    'project_admin',
    'service_admin',
    'developer',
    'viewer',
    'agent',
    'security_admin',
    'audit_admin'
);

CREATE TYPE audit_event_type AS ENUM (
    'create',
    'read',
    'update', 
    'delete',
    'rotate',
    'access',
    'admin',
    'auth',
    'export',
    'import',
    'emergency'
);

CREATE TYPE approval_status AS ENUM (
    'pending',
    'approved',
    'rejected',
    'expired',
    'cancelled'
);

-- Organizations table
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    settings JSONB DEFAULT '{}',
    compliance_requirements TEXT[],
    
    CONSTRAINT organizations_name_unique UNIQUE (name)
);

-- Environments table
CREATE TABLE environments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    environment_type environment_type NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    settings JSONB DEFAULT '{}',
    
    CONSTRAINT environments_org_name_unique UNIQUE (organization_id, name)
);

-- Projects table  
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    environment_id UUID NOT NULL REFERENCES environments(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    settings JSONB DEFAULT '{}',
    repository_url VARCHAR(500),
    
    CONSTRAINT projects_env_name_unique UNIQUE (environment_id, name)
);

-- Services table
CREATE TABLE services (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    service_url VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    settings JSONB DEFAULT '{}',
    
    CONSTRAINT services_project_name_unique UNIQUE (project_id, name)
);

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(320) NOT NULL,
    username VARCHAR(100),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    password_hash VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,
    mfa_enabled BOOLEAN DEFAULT FALSE,
    mfa_secret VARCHAR(255),
    settings JSONB DEFAULT '{}',
    
    CONSTRAINT users_email_unique UNIQUE (email),
    CONSTRAINT users_username_unique UNIQUE (username)
);

-- User roles table
CREATE TABLE user_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role user_role NOT NULL,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    environment_id UUID REFERENCES environments(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    service_id UUID REFERENCES services(id) ON DELETE CASCADE,
    granted_by UUID NOT NULL REFERENCES users(id),
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    
    CONSTRAINT user_roles_unique UNIQUE (user_id, role, organization_id, environment_id, project_id, service_id)
);

-- Encryption keys table (for key versioning and rotation)
CREATE TABLE encryption_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key_version INTEGER NOT NULL,
    key_hash VARCHAR(255) NOT NULL, -- Hash of the key for identification
    algorithm VARCHAR(50) NOT NULL DEFAULT 'AES-256-GCM',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    hsm_key_id VARCHAR(255), -- HSM key identifier
    key_metadata JSONB DEFAULT '{}',
    
    CONSTRAINT encryption_keys_version_unique UNIQUE (key_version)
);

-- Credentials table (main credential storage)
CREATE TABLE credentials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    credential_type credential_type NOT NULL,
    
    -- Hierarchy references
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    environment_id UUID REFERENCES environments(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    service_id UUID REFERENCES services(id) ON DELETE CASCADE,
    
    -- Ownership and access
    owner_id UUID NOT NULL REFERENCES users(id),
    created_by UUID NOT NULL REFERENCES users(id),
    
    -- Encrypted credential data
    encrypted_data BYTEA NOT NULL, -- Encrypted credential payload
    encryption_key_version INTEGER NOT NULL REFERENCES encryption_keys(key_version),
    salt BYTEA NOT NULL, -- Unique salt for this credential
    nonce BYTEA NOT NULL, -- Nonce/IV for encryption
    auth_tag BYTEA NOT NULL, -- Authentication tag for GCM mode
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_accessed TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    
    -- Rotation settings
    rotation_interval_days INTEGER DEFAULT 90,
    next_rotation TIMESTAMP WITH TIME ZONE,
    auto_rotate BOOLEAN DEFAULT FALSE,
    
    -- Security and compliance
    risk_level risk_level DEFAULT 'medium',
    compliance_labels TEXT[],
    tags TEXT[],
    
    -- Access tracking
    access_count BIGINT DEFAULT 0,
    
    -- Backup and audit settings
    backup_enabled BOOLEAN DEFAULT TRUE,
    audit_enabled BOOLEAN DEFAULT TRUE,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP WITH TIME ZONE,
    deleted_by UUID REFERENCES users(id),
    
    -- Additional metadata
    metadata JSONB DEFAULT '{}',
    
    CONSTRAINT credentials_name_scope_unique UNIQUE (name, organization_id, environment_id, project_id, service_id)
);

-- Credential sharing table (for shared access)
CREATE TABLE credential_shares (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    credential_id UUID NOT NULL REFERENCES credentials(id) ON DELETE CASCADE,
    shared_with_user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    shared_with_role user_role,
    shared_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    permissions JSONB DEFAULT '{"read": true, "write": false}',
    is_active BOOLEAN DEFAULT TRUE,
    
    CONSTRAINT credential_shares_unique UNIQUE (credential_id, shared_with_user_id, shared_with_role)
);

-- Audit log table
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type audit_event_type NOT NULL,
    user_id UUID REFERENCES users(id),
    credential_id UUID REFERENCES credentials(id),
    
    -- Event details
    action VARCHAR(255) NOT NULL,
    result VARCHAR(50) NOT NULL, -- success, failure, partial
    
    -- Request context
    ip_address INET,
    user_agent TEXT,
    session_id UUID,
    request_id UUID,
    
    -- Timing
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    duration_ms INTEGER,
    
    -- Security context
    risk_score FLOAT,
    anomaly_detected BOOLEAN DEFAULT FALSE,
    mfa_verified BOOLEAN,
    
    -- Compliance
    compliance_flags TEXT[],
    
    -- Additional context
    metadata JSONB DEFAULT '{}',
    
    -- Indexes for performance
    INDEX idx_audit_log_timestamp (timestamp),
    INDEX idx_audit_log_user_id (user_id),
    INDEX idx_audit_log_credential_id (credential_id),
    INDEX idx_audit_log_event_type (event_type)
);

-- Multi-signature approval requests
CREATE TABLE approval_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operation_type VARCHAR(100) NOT NULL,
    operation_details JSONB NOT NULL,
    
    -- Request context
    requesting_user_id UUID NOT NULL REFERENCES users(id),
    credential_id UUID REFERENCES credentials(id),
    
    -- Approval requirements
    required_approvals INTEGER NOT NULL DEFAULT 2,
    received_approvals INTEGER DEFAULT 0,
    
    -- Status and timing
    status approval_status DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Justification
    business_justification TEXT NOT NULL,
    
    -- Additional context
    metadata JSONB DEFAULT '{}'
);

-- Individual approvals for multi-sig requests
CREATE TABLE approvals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    approval_request_id UUID NOT NULL REFERENCES approval_requests(id) ON DELETE CASCADE,
    approver_id UUID NOT NULL REFERENCES users(id),
    
    -- Approval decision
    approved BOOLEAN NOT NULL,
    reason TEXT,
    
    -- Cryptographic signature
    signature BYTEA,
    signature_algorithm VARCHAR(50),
    
    -- Timing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Additional context
    metadata JSONB DEFAULT '{}',
    
    CONSTRAINT approvals_unique UNIQUE (approval_request_id, approver_id)
);

-- Credential escrow for business continuity
CREATE TABLE credential_escrow (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    credential_id UUID NOT NULL REFERENCES credentials(id) ON DELETE CASCADE,
    
    -- Escrow details
    escrow_type VARCHAR(50) NOT NULL, -- business_continuity, legal_hold, emergency_access
    business_justification TEXT NOT NULL,
    
    -- Ownership
    owner_id UUID NOT NULL REFERENCES users(id),
    escrowed_by UUID NOT NULL REFERENCES users(id),
    
    -- Recovery contacts
    recovery_contacts JSONB DEFAULT '[]',
    
    -- Encrypted escrow data
    encrypted_escrow_data BYTEA NOT NULL,
    escrow_key_version INTEGER NOT NULL REFERENCES encryption_keys(key_version),
    escrow_salt BYTEA NOT NULL,
    escrow_nonce BYTEA NOT NULL,
    escrow_auth_tag BYTEA NOT NULL,
    
    -- Status and timing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Additional context
    metadata JSONB DEFAULT '{}'
);

-- Shamir secret sharing for distributed key management
CREATE TABLE secret_shares (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key_id VARCHAR(255) NOT NULL,
    share_number INTEGER NOT NULL,
    total_shares INTEGER NOT NULL,
    threshold INTEGER NOT NULL,
    
    -- Share data (encrypted)
    encrypted_share BYTEA NOT NULL,
    share_hash VARCHAR(255) NOT NULL,
    
    -- Ownership
    owner_id UUID NOT NULL REFERENCES users(id),
    created_by UUID NOT NULL REFERENCES users(id),
    
    -- Status and timing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Additional context
    metadata JSONB DEFAULT '{}',
    
    CONSTRAINT secret_shares_unique UNIQUE (key_id, share_number)
);

-- Sessions table for security session management
CREATE TABLE security_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) NOT NULL,
    
    -- Security level
    security_level VARCHAR(50) NOT NULL DEFAULT 'standard',
    
    -- Timing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Context
    ip_address INET,
    user_agent TEXT,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    revoked_by UUID REFERENCES users(id),
    
    -- Additional context
    metadata JSONB DEFAULT '{}',
    
    CONSTRAINT security_sessions_token_unique UNIQUE (session_token)
);

-- Threat intelligence and security events
CREATE TABLE security_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_category VARCHAR(100) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    
    -- Event details
    title VARCHAR(500) NOT NULL,
    description TEXT,
    severity VARCHAR(50) NOT NULL,
    confidence_score FLOAT,
    
    -- Affected resources
    affected_user_id UUID REFERENCES users(id),
    affected_credential_id UUID REFERENCES credentials(id),
    affected_systems TEXT[],
    
    -- Indicators
    indicators JSONB DEFAULT '{}',
    
    -- MITRE ATT&CK mapping
    mitre_tactics TEXT[],
    mitre_techniques TEXT[],
    
    -- Response
    response_status VARCHAR(50) DEFAULT 'open',
    response_actions JSONB DEFAULT '[]',
    
    -- Timing
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    
    -- Additional context
    metadata JSONB DEFAULT '{}'
);

-- Compliance reports
CREATE TABLE compliance_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_type VARCHAR(100) NOT NULL,
    report_date DATE NOT NULL,
    
    -- Scope
    organization_id UUID REFERENCES organizations(id),
    environment_id UUID REFERENCES environments(id),
    
    -- Report data
    report_data JSONB NOT NULL,
    summary JSONB DEFAULT '{}',
    
    -- Status
    status VARCHAR(50) DEFAULT 'generated',
    generated_by UUID NOT NULL REFERENCES users(id),
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Additional context
    metadata JSONB DEFAULT '{}',
    
    CONSTRAINT compliance_reports_unique UNIQUE (report_type, report_date, organization_id, environment_id)
);

-- Create indexes for performance
CREATE INDEX idx_credentials_organization_id ON credentials(organization_id);
CREATE INDEX idx_credentials_environment_id ON credentials(environment_id);
CREATE INDEX idx_credentials_project_id ON credentials(project_id);
CREATE INDEX idx_credentials_service_id ON credentials(service_id);
CREATE INDEX idx_credentials_owner_id ON credentials(owner_id);
CREATE INDEX idx_credentials_type ON credentials(credential_type);
CREATE INDEX idx_credentials_expires_at ON credentials(expires_at);
CREATE INDEX idx_credentials_next_rotation ON credentials(next_rotation);
CREATE INDEX idx_credentials_risk_level ON credentials(risk_level);
CREATE INDEX idx_credentials_tags ON credentials USING GIN(tags);
CREATE INDEX idx_credentials_compliance_labels ON credentials USING GIN(compliance_labels);
CREATE INDEX idx_credentials_active ON credentials(is_active) WHERE is_active = true;
CREATE INDEX idx_credentials_deleted ON credentials(is_deleted, deleted_at) WHERE is_deleted = true;

CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX idx_user_roles_organization_id ON user_roles(organization_id);
CREATE INDEX idx_user_roles_active ON user_roles(is_active) WHERE is_active = true;

CREATE INDEX idx_audit_log_composite ON audit_log(timestamp DESC, user_id, event_type);
CREATE INDEX idx_audit_log_credential_composite ON audit_log(credential_id, timestamp DESC);
CREATE INDEX idx_audit_log_risk_score ON audit_log(risk_score) WHERE risk_score > 0.7;

CREATE INDEX idx_approval_requests_status ON approval_requests(status);
CREATE INDEX idx_approval_requests_requesting_user ON approval_requests(requesting_user_id);
CREATE INDEX idx_approval_requests_expires_at ON approval_requests(expires_at);

CREATE INDEX idx_security_sessions_user_id ON security_sessions(user_id);
CREATE INDEX idx_security_sessions_expires_at ON security_sessions(expires_at);
CREATE INDEX idx_security_sessions_active ON security_sessions(is_active) WHERE is_active = true;

CREATE INDEX idx_security_events_category ON security_events(event_category);
CREATE INDEX idx_security_events_severity ON security_events(severity);
CREATE INDEX idx_security_events_detected_at ON security_events(detected_at DESC);
CREATE INDEX idx_security_events_status ON security_events(response_status);

-- Create full-text search indexes
CREATE INDEX idx_credentials_search ON credentials USING GIN(to_tsvector('english', name || ' ' || COALESCE(description, '')));
CREATE INDEX idx_audit_log_search ON audit_log USING GIN(to_tsvector('english', action || ' ' || COALESCE(metadata::text, '')));

-- Create triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_environments_updated_at BEFORE UPDATE ON environments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_services_updated_at BEFORE UPDATE ON services FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_credentials_updated_at BEFORE UPDATE ON credentials FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create trigger to update access count and last_accessed
CREATE OR REPLACE FUNCTION update_credential_access()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE credentials 
    SET access_count = access_count + 1,
        last_accessed = NOW()
    WHERE id = NEW.credential_id
    AND NEW.event_type = 'access'
    AND NEW.result = 'success';
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_credential_access_trigger 
AFTER INSERT ON audit_log 
FOR EACH ROW 
EXECUTE FUNCTION update_credential_access();

-- Create views for common queries
CREATE VIEW active_credentials AS
SELECT 
    c.*,
    o.name as organization_name,
    e.name as environment_name,
    e.environment_type,
    p.name as project_name,
    s.name as service_name,
    u.email as owner_email
FROM credentials c
JOIN organizations o ON c.organization_id = o.id
LEFT JOIN environments e ON c.environment_id = e.id
LEFT JOIN projects p ON c.project_id = p.id
LEFT JOIN services s ON c.service_id = s.id
JOIN users u ON c.owner_id = u.id
WHERE c.is_active = true AND c.is_deleted = false;

CREATE VIEW credential_access_summary AS
SELECT 
    c.id,
    c.name,
    c.credential_type,
    c.risk_level,
    c.access_count,
    c.last_accessed,
    COUNT(al.id) as audit_events,
    MAX(al.timestamp) as last_audit_event
FROM credentials c
LEFT JOIN audit_log al ON c.id = al.credential_id
WHERE c.is_active = true AND c.is_deleted = false
GROUP BY c.id, c.name, c.credential_type, c.risk_level, c.access_count, c.last_accessed;

CREATE VIEW user_permissions_summary AS
SELECT 
    u.id as user_id,
    u.email,
    ur.role,
    o.name as organization_name,
    e.name as environment_name,
    p.name as project_name,
    s.name as service_name,
    ur.granted_at,
    ur.expires_at
FROM users u
JOIN user_roles ur ON u.id = ur.user_id
LEFT JOIN organizations o ON ur.organization_id = o.id
LEFT JOIN environments e ON ur.environment_id = e.id
LEFT JOIN projects p ON ur.project_id = p.id
LEFT JOIN services s ON ur.service_id = s.id
WHERE ur.is_active = true;

-- Create row-level security policies (RLS)
ALTER TABLE credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;

-- Example RLS policy for credentials (would need to be customized based on application logic)
CREATE POLICY credential_access_policy ON credentials
    FOR ALL
    TO vault_app_role
    USING (
        -- Users can access credentials they own
        owner_id = current_setting('app.current_user_id')::uuid
        OR
        -- Users can access credentials shared with them
        id IN (
            SELECT credential_id 
            FROM credential_shares 
            WHERE shared_with_user_id = current_setting('app.current_user_id')::uuid
            AND is_active = true
            AND (expires_at IS NULL OR expires_at > NOW())
        )
        OR
        -- Users with appropriate roles can access credentials in their scope
        EXISTS (
            SELECT 1 FROM user_roles ur
            WHERE ur.user_id = current_setting('app.current_user_id')::uuid
            AND ur.is_active = true
            AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
            AND (
                (ur.role IN ('super_admin', 'security_admin', 'audit_admin'))
                OR
                (ur.role = 'organization_admin' AND ur.organization_id = credentials.organization_id)
                OR
                (ur.role = 'environment_admin' AND ur.environment_id = credentials.environment_id)
                OR
                (ur.role = 'project_admin' AND ur.project_id = credentials.project_id)
                OR
                (ur.role = 'service_admin' AND ur.service_id = credentials.service_id)
            )
        )
    );

-- Grant permissions to application role
GRANT USAGE ON SCHEMA public TO vault_app_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO vault_app_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO vault_app_role;

-- Create application-specific database role
-- CREATE ROLE vault_app_role WITH LOGIN PASSWORD 'secure_password_here';

-- Add comments for documentation
COMMENT ON TABLE credentials IS 'Main table for storing encrypted credentials with hierarchical organization';
COMMENT ON COLUMN credentials.encrypted_data IS 'AES-256-GCM encrypted credential payload';
COMMENT ON COLUMN credentials.salt IS 'Unique cryptographic salt for key derivation';
COMMENT ON COLUMN credentials.nonce IS 'Nonce/IV for AES-GCM encryption';
COMMENT ON COLUMN credentials.auth_tag IS 'Authentication tag for verifying data integrity';

COMMENT ON TABLE audit_log IS 'Comprehensive audit trail for all vault operations';
COMMENT ON TABLE approval_requests IS 'Multi-signature approval workflow for sensitive operations';
COMMENT ON TABLE credential_escrow IS 'Business continuity escrow system for critical credentials';
COMMENT ON TABLE secret_shares IS 'Shamir secret sharing for distributed key management';
COMMENT ON TABLE security_events IS 'Security events and threat intelligence storage';

-- Schema version tracking
CREATE TABLE schema_version (
    version VARCHAR(20) PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    description TEXT
);

INSERT INTO schema_version (version, description) 
VALUES ('1.0.0', 'Initial enterprise credential vault schema');