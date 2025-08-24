# MCP Hub Authentication and Access Control Guide

## Overview

The MCP Hub Authentication and Access Control system provides enterprise-grade security for MCP (Model Context Protocol) server management. This comprehensive security layer includes user management, API key authentication, role-based access control, tool-level permissions, rate limiting, and advanced security analytics powered by hAIveMind.

## Features

### 🔐 Authentication Methods
- **Username/Password Authentication**: Traditional login with secure password hashing (bcrypt)
- **API Key Authentication**: Programmatic access with secure API keys
- **JWT Token Support**: Stateless authentication for distributed systems
- **Session Management**: Secure session handling with Redis caching

### 👥 User Management
- **User Accounts**: Create and manage user accounts with roles and permissions
- **Role-Based Access Control (RBAC)**: Admin, User, and Read-Only roles
- **Custom Permissions**: Fine-grained permission system for specific operations
- **Account Lifecycle**: User activation, deactivation, and management

### 🔑 API Key Management
- **Secure Key Generation**: Cryptographically secure API key generation
- **Key Expiration**: Configurable expiration dates for API keys
- **Usage Tracking**: Monitor API key usage and last access times
- **Key Revocation**: Immediate revocation of compromised keys

### 🖥️ Per-Server Authentication
- **Server-Specific Access Control**: Configure authentication per MCP server
- **Tool-Level Permissions**: Control access to specific tools within servers
- **Rate Limiting**: Per-server and per-role rate limiting
- **Audit Levels**: Configurable audit logging levels (minimal, standard, detailed)

### 📊 Security Analytics & hAIveMind Integration
- **Behavioral Analysis**: AI-powered user behavior profiling
- **Anomaly Detection**: Detect unusual login patterns and tool usage
- **Threat Intelligence**: Generate threat intelligence from security patterns
- **Risk Scoring**: Dynamic user risk assessment
- **Security Recommendations**: Automated security improvement suggestions

### 🔍 Audit Logging
- **Comprehensive Logging**: All authentication and authorization events
- **Risk-Based Classification**: Events classified by risk level
- **Retention Policies**: Configurable log retention periods
- **GDPR Compliance**: Data export and deletion capabilities

## Quick Start

### 1. Setup Authentication System

Run the setup script to initialize the authentication system:

```bash
python scripts/setup_mcp_auth.py
```

This will:
- Initialize the authentication database
- Create an admin user account
- Generate secure API keys
- Configure default server authentication
- Update configuration with secure settings

### 2. Start MCP Hub with Authentication

```bash
python src/mcp_aggregator.py
```

### 3. Access the Authentication Dashboard

Navigate to `http://localhost:8910/auth` to access the authentication management dashboard.

## Configuration

### Security Configuration

The authentication system is configured in `config/config.json` under the `security` section:

```json
{
  "security": {
    "enable_auth": true,
    "jwt_secret": "${HAIVEMIND_JWT_SECRET:-change-this-secret-key}",
    "session_timeout_hours": 24,
    "rate_limiting": {
      "enabled": true,
      "requests_per_minute": 120,
      "burst_limit": 10
    },
    "audit": {
      "enabled": true,
      "retention_days": 90,
      "log_sensitive_data": false
    },
    "password_policy": {
      "min_length": 8,
      "require_uppercase": true,
      "require_lowercase": true,
      "require_numbers": true,
      "require_special_chars": false
    },
    "ip_whitelist": ["127.0.0.1", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
  }
}
```

### Database Configuration

Authentication data is stored in SQLite by default:

```json
{
  "storage": {
    "auth_db": "data/auth.db",
    "redis": {
      "host": "localhost",
      "port": 6379,
      "db": 1,
      "enable_cache": true
    }
  }
}
```

## User Management

### Creating Users

#### Via Dashboard
1. Navigate to `http://localhost:8910/auth/users`
2. Fill in the user creation form
3. Select appropriate role and permissions

#### Via MCP Tools
```python
# Using MCP tools
result = await create_user_account(
    username="newuser",
    password="securepassword123",
    role="user",
    permissions=["read", "write"]
)
```

#### Via API
```bash
curl -X POST http://localhost:8910/api/auth/users \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "username": "newuser",
    "password": "securepassword123",
    "role": "user",
    "permissions": ["read", "write"]
  }'
```

### User Roles

- **Admin**: Full access to all systems and management functions
- **User**: Standard access to tools and servers based on permissions
- **Read-Only**: Read-only access to tools and data

## API Key Management

### Creating API Keys

#### Via Dashboard
1. Navigate to `http://localhost:8910/auth/api-keys`
2. Fill in the API key creation form
3. Configure expiration and server access

#### Via MCP Tools
```python
result = await create_api_key(
    user_id="user_123",
    key_name="Production API Key",
    role="user",
    server_access={
        "memory-server": ["store_memory", "retrieve_memory"],
        "file-server": ["*"]
    },
    expires_days=90
)
```

### Using API Keys

API keys can be used in several ways:

#### Authorization Header
```bash
curl -H "Authorization: Bearer mcp_your_api_key_here" \
  http://localhost:8950/api/endpoint
```

#### Query Parameter
```bash
curl "http://localhost:8950/api/endpoint?api_key=mcp_your_api_key_here"
```

## Server Authentication Configuration

### Configuring Server Access

Each MCP server can have its own authentication configuration:

```python
await configure_server_auth(
    server_id="memory-server",
    auth_required=True,
    allowed_roles=["admin", "user"],
    tool_permissions={
        "store_memory": ["admin", "user"],
        "delete_memory": ["admin"],
        "bulk_delete_memories": ["admin"]
    },
    rate_limits={
        "admin": 1000,
        "user": 200,
        "readonly": 100
    },
    audit_level="standard"
)
```

### Tool-Level Permissions

Control access to specific tools within servers:

```json
{
  "tool_permissions": {
    "store_memory": ["admin", "user"],
    "retrieve_memory": ["admin", "user", "readonly"],
    "delete_memory": ["admin"],
    "gdpr_delete_user_data": ["admin"]
  }
}
```

## Rate Limiting

### Configuration

Rate limiting is configured per role and per server:

```json
{
  "rate_limits": {
    "admin": 1000,
    "user": 200,
    "readonly": 100
  }
}
```

### Implementation

Rate limiting uses Redis for distributed tracking with sliding window algorithm:
- Tracks requests per minute per user/server combination
- Automatically blocks requests exceeding limits
- Logs violations for security analysis

## Security Analytics

### hAIveMind Integration

The authentication system integrates with hAIveMind for advanced security analytics:

#### Behavioral Analysis
- **Login Pattern Analysis**: Detects unusual login times and frequencies
- **Tool Usage Profiling**: Monitors tool usage patterns for anomalies
- **IP Address Tracking**: Identifies suspicious IP address changes
- **Session Analysis**: Analyzes session duration and activity patterns

#### Threat Detection
- **Brute Force Detection**: Identifies coordinated attack attempts
- **Privilege Escalation**: Detects unauthorized privilege escalation attempts
- **Account Compromise**: Identifies potentially compromised accounts
- **Insider Threats**: Detects suspicious behavior from legitimate users

#### Risk Scoring
Dynamic risk scores are calculated based on:
- Recent failed login attempts
- IP address diversity
- Unusual login times
- High-risk tool usage
- Historical behavior patterns

### Security Recommendations

The system automatically generates security recommendations:

```python
recommendations = await get_security_analytics(days=7)
```

Example recommendations:
- Enable MFA for high-risk users
- Implement additional rate limiting
- Review user permissions
- Investigate suspicious activities

## Audit Logging

### Event Types

The system logs various security events:
- **Authentication Events**: Login attempts, API key usage
- **Authorization Events**: Permission checks, access denials
- **Tool Execution**: All tool calls with parameters and results
- **Administrative Actions**: User creation, permission changes
- **Security Events**: Rate limit violations, suspicious activities

### Audit Levels

- **Minimal**: Basic authentication and authorization events
- **Standard**: All security-relevant events with moderate detail
- **Detailed**: Comprehensive logging including tool parameters and results

### Viewing Audit Logs

#### Via Dashboard
Navigate to `http://localhost:8910/auth/security` to view:
- Security analytics
- Audit event logs
- Risk assessments
- Threat intelligence

#### Via MCP Tools
```python
events = await audit_security_events(
    event_type="login_failed",
    hours=24,
    risk_level="high"
)
```

## Integration Examples

### Claude Desktop Integration

Configure Claude Desktop to use MCP Hub with authentication:

```json
{
  "mcpServers": {
    "mcp-hub": {
      "command": "python",
      "args": ["src/mcp_aggregator.py"],
      "env": {
        "MCP_HUB_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

### Programmatic Access

```python
import requests

# Authenticate and get tools
headers = {"Authorization": "Bearer your_api_key_here"}
response = requests.get("http://localhost:8950/tools", headers=headers)
tools = response.json()

# Execute tool with authentication
tool_request = {
    "name": "store_memory",
    "arguments": {
        "content": "Test memory",
        "category": "test"
    }
}

response = requests.post(
    "http://localhost:8950/tools/call",
    headers=headers,
    json=tool_request
)
```

## Security Best Practices

### Password Security
- Use strong, unique passwords
- Enable password complexity requirements
- Implement password rotation policies
- Consider multi-factor authentication

### API Key Security
- Generate keys with appropriate expiration dates
- Use least-privilege principle for key permissions
- Rotate keys regularly
- Monitor key usage for anomalies

### Network Security
- Use IP whitelisting for production environments
- Implement TLS/SSL for all communications
- Consider VPN access for sensitive operations
- Monitor network traffic for anomalies

### Operational Security
- Regularly review user permissions
- Monitor audit logs for suspicious activities
- Implement incident response procedures
- Keep security configurations up to date

## Troubleshooting

### Common Issues

#### Authentication Failures
```bash
# Check user status
python -c "
import asyncio
from src.mcp_auth_tools import MCPAuthTools
# ... check user account status
"
```

#### API Key Issues
- Verify key hasn't expired
- Check key permissions for specific servers/tools
- Ensure key is active and not revoked

#### Rate Limiting
- Check current rate limits for user role
- Review recent request patterns
- Consider adjusting limits if legitimate

### Debugging

Enable debug logging:
```bash
export PYTHONPATH=/path/to/mcp-hub/src
export MCP_DEBUG=true
python src/mcp_aggregator.py
```

### Support

For additional support:
1. Check the audit logs for detailed error information
2. Review security analytics for patterns
3. Consult the hAIveMind memory for related issues
4. Enable detailed audit logging for troubleshooting

## Advanced Configuration

### Custom Authentication Providers

The system can be extended with custom authentication providers:

```python
class CustomAuthProvider:
    async def authenticate(self, credentials):
        # Custom authentication logic
        pass
```

### Integration with External Systems

- **LDAP/Active Directory**: Integrate with existing directory services
- **OAuth/SAML**: Support for enterprise SSO systems
- **Multi-Factor Authentication**: Add MFA support
- **Hardware Security Modules**: Use HSMs for key management

### High Availability

For production deployments:
- Use Redis Cluster for session storage
- Implement database replication
- Deploy multiple MCP Hub instances
- Use load balancers with session affinity

## Compliance and Privacy

### GDPR Compliance

The system includes GDPR-compliant features:
- **Right to be Forgotten**: Complete user data deletion
- **Data Portability**: Export user data in standard formats
- **Consent Management**: Track and manage user consent
- **Data Minimization**: Configurable data retention policies

### Security Standards

The authentication system follows security best practices:
- **OWASP Guidelines**: Secure coding practices
- **NIST Framework**: Security control implementation
- **SOC 2 Type II**: Audit-ready logging and controls
- **ISO 27001**: Information security management

## Conclusion

The MCP Hub Authentication and Access Control system provides enterprise-grade security for MCP server management. With its comprehensive feature set, hAIveMind integration, and flexible configuration options, it ensures secure and compliant operation of your MCP infrastructure.

For questions or support, consult the audit logs, security analytics, or hAIveMind memory system for detailed insights and recommendations.