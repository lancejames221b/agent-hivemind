# hAIveMind Enterprise Credential Vault - Deployment Guide

**Author:** Lance James, Unit 221B  
**Date:** 2025-08-25  
**Version:** 1.0  

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Infrastructure Requirements](#infrastructure-requirements)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Security Setup](#security-setup)
7. [Database Setup](#database-setup)
8. [SSL/TLS Configuration](#ssltls-configuration)
9. [HSM Integration](#hsm-integration)
10. [LDAP/AD Integration](#ldapad-integration)
11. [Monitoring and Logging](#monitoring-and-logging)
12. [Backup and Recovery](#backup-and-recovery)
13. [High Availability](#high-availability)
14. [Performance Tuning](#performance-tuning)
15. [Security Hardening](#security-hardening)
16. [Troubleshooting](#troubleshooting)
17. [Maintenance](#maintenance)

## Overview

The hAIveMind Enterprise Credential Vault is a comprehensive, zero-knowledge credential management system designed for enterprise environments. This guide covers the complete deployment process from infrastructure setup to production readiness.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Load Balancer (HAProxy/NGINX)           │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────┼───────────────────────────────────────┐
│                 API Gateway                                 │
└─────────────────────┬───────────────────────────────────────┘
                      │
    ┌─────────────────┼─────────────────┐
    │                 │                 │
┌───▼────┐    ┌──────▼──────┐    ┌─────▼─────┐
│Vault   │    │Vault        │    │Vault      │
│API     │    │API          │    │API        │
│Server 1│    │Server 2     │    │Server 3   │
└───┬────┘    └──────┬──────┘    └─────┬─────┘
    │                │                 │
    └─────────────────┼─────────────────┘
                      │
    ┌─────────────────┼─────────────────┐
    │                 │                 │
┌───▼────┐    ┌──────▼──────┐    ┌─────▼─────┐
│PostgreSQL   │Redis        │    │HSM        │
│Primary      │Cluster      │    │Cluster    │
└─────────────┘└─────────────┘    └───────────┘
```

## Prerequisites

### System Requirements

**Minimum Requirements (Development/Testing):**
- CPU: 4 cores
- RAM: 8 GB
- Storage: 100 GB SSD
- Network: 1 Gbps

**Recommended Requirements (Production):**
- CPU: 8+ cores
- RAM: 32+ GB
- Storage: 500+ GB NVMe SSD
- Network: 10 Gbps

### Software Dependencies

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- NGINX or HAProxy (for load balancing)
- Docker and Docker Compose (optional)
- Kubernetes (for container orchestration)

### Network Requirements

- Inbound ports: 443 (HTTPS), 8080 (API), 9090 (Metrics)
- Outbound ports: 443 (HTTPS), 636 (LDAPS), 5432 (PostgreSQL), 6379 (Redis)
- Internal communication: All vault components must be able to communicate

## Infrastructure Requirements

### Production Environment

**Database Tier:**
- PostgreSQL 15+ with SSL/TLS encryption
- Minimum 3-node cluster for high availability
- Automated backup and point-in-time recovery
- Connection pooling (PgBouncer recommended)

**Cache Tier:**
- Redis 7+ cluster with SSL/TLS encryption
- Minimum 3-node cluster with replication
- Persistent storage for session data
- Memory optimization for caching

**Application Tier:**
- Minimum 3 API server instances
- Load balancer with health checks
- Auto-scaling capabilities
- Container orchestration (Kubernetes recommended)

**Security Tier:**
- Hardware Security Module (HSM) integration
- Certificate management system
- Network segmentation and firewalls
- Intrusion detection and prevention

## Installation

### Method 1: Docker Compose (Recommended for Development)

1. **Clone the repository:**
```bash
git clone https://github.com/unit221b/haivemind-vault.git
cd haivemind-vault
```

2. **Create environment file:**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Start services:**
```bash
docker-compose up -d
```

### Method 2: Kubernetes (Recommended for Production)

1. **Create namespace:**
```bash
kubectl create namespace haivemind-vault
```

2. **Deploy PostgreSQL:**
```bash
kubectl apply -f k8s/postgresql/
```

3. **Deploy Redis:**
```bash
kubectl apply -f k8s/redis/
```

4. **Deploy Vault API:**
```bash
kubectl apply -f k8s/vault-api/
```

5. **Deploy Ingress:**
```bash
kubectl apply -f k8s/ingress/
```

### Method 3: Manual Installation

1. **Install Python dependencies:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Install system dependencies:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install postgresql-client redis-tools nginx

# RHEL/CentOS
sudo yum install postgresql redis nginx
```

3. **Create application user:**
```bash
sudo useradd -r -s /bin/false vault
sudo mkdir -p /opt/vault
sudo chown vault:vault /opt/vault
```

4. **Install application:**
```bash
sudo cp -r src/ /opt/vault/
sudo cp config/ /opt/vault/
sudo chown -R vault:vault /opt/vault/
```

## Configuration

### Environment Variables

Create `/opt/vault/.env` file:

```bash
# Database Configuration
VAULT_DATABASE_URL=postgresql://vault:secure_password@localhost:5432/vault?sslmode=require
VAULT_REDIS_URL=redis://localhost:6379/0
VAULT_REDIS_PASSWORD=secure_redis_password

# Security Configuration
VAULT_JWT_SECRET=your-256-bit-jwt-secret-key-here
HAIVEMIND_JWT_SECRET=your-haivemind-jwt-secret-here
HAIVEMIND_ADMIN_TOKEN=your-admin-token-here
HAIVEMIND_AGENT_TOKEN=your-agent-token-here

# LDAP Configuration
LDAP_SERVER=ldap.company.com
LDAP_BIND_DN=CN=vault-service,OU=Service Accounts,DC=company,DC=com
LDAP_BIND_PASSWORD=ldap_service_password
LDAP_BASE_DN=DC=company,DC=com

# HSM Configuration
YUBIHSM2_AUTH_KEY=your-hsm-auth-key
AWS_CLOUDHSM_CLUSTER_ID=cluster-abc123
AWS_CLOUDHSM_USER=vault-user
AWS_CLOUDHSM_PASSWORD=hsm-password

# Backup Configuration
VAULT_BACKUP_S3_BUCKET=vault-backups-company
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key

# Monitoring Configuration
SMTP_SERVER=smtp.company.com
SMTP_USERNAME=vault-alerts@company.com
SMTP_PASSWORD=smtp_password
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
PAGERDUTY_INTEGRATION_KEY=your-pagerduty-key

# hAIveMind Configuration
HAIVEMIND_MACHINE_ID=vault-production-01
HAIVEMIND_MEMORY_SERVER_URL=http://haivemind-memory:8900
HAIVEMIND_API_TOKEN=your-haivemind-api-token
```

### Application Configuration

Edit `/opt/vault/config/enterprise_vault_config.json`:

```json
{
  "vault": {
    "environment": "production",
    "api": {
      "host": "0.0.0.0",
      "port": 8080,
      "workers": 8
    },
    "database": {
      "pool_size": 50,
      "max_overflow": 100
    }
  }
}
```

## Security Setup

### SSL/TLS Certificates

1. **Generate private key:**
```bash
openssl genrsa -out /etc/ssl/private/vault.key 4096
chmod 600 /etc/ssl/private/vault.key
```

2. **Create certificate signing request:**
```bash
openssl req -new -key /etc/ssl/private/vault.key -out vault.csr
```

3. **Generate self-signed certificate (development only):**
```bash
openssl x509 -req -days 365 -in vault.csr -signkey /etc/ssl/private/vault.key -out /etc/ssl/certs/vault.crt
```

4. **For production, use certificates from a trusted CA or Let's Encrypt:**
```bash
certbot certonly --nginx -d vault.company.com
```

### Firewall Configuration

```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 22/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8080/tcp
sudo ufw enable

# RHEL/CentOS (firewalld)
sudo firewall-cmd --permanent --add-port=22/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload
```

## Database Setup

### PostgreSQL Installation and Configuration

1. **Install PostgreSQL:**
```bash
# Ubuntu/Debian
sudo apt-get install postgresql-15 postgresql-contrib-15

# RHEL/CentOS
sudo yum install postgresql15-server postgresql15-contrib
sudo postgresql-15-setup initdb
```

2. **Configure PostgreSQL:**

Edit `/etc/postgresql/15/main/postgresql.conf`:
```
listen_addresses = '*'
ssl = on
ssl_cert_file = '/etc/ssl/certs/postgresql.crt'
ssl_key_file = '/etc/ssl/private/postgresql.key'
ssl_ca_file = '/etc/ssl/certs/ca-bundle.crt'
max_connections = 200
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
```

Edit `/etc/postgresql/15/main/pg_hba.conf`:
```
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             postgres                                peer
local   all             all                                     md5
hostssl vault           vault           10.0.0.0/8              md5
hostssl vault           vault           172.16.0.0/12           md5
hostssl vault           vault           192.168.0.0/16          md5
```

3. **Create database and user:**
```sql
CREATE USER vault WITH ENCRYPTED PASSWORD 'secure_password';
CREATE DATABASE vault OWNER vault;
GRANT ALL PRIVILEGES ON DATABASE vault TO vault;
```

4. **Initialize database schema:**
```bash
psql -h localhost -U vault -d vault -f config/vault_database_schema.sql
```

### Redis Configuration

1. **Install Redis:**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# RHEL/CentOS
sudo yum install redis
```

2. **Configure Redis:**

Edit `/etc/redis/redis.conf`:
```
bind 127.0.0.1 10.0.0.100
port 6379
requirepass secure_redis_password
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

3. **Enable SSL/TLS (optional):**
```
tls-port 6380
tls-cert-file /etc/ssl/certs/redis.crt
tls-key-file /etc/ssl/private/redis.key
tls-ca-cert-file /etc/ssl/certs/ca-bundle.crt
```

## HSM Integration

### YubiHSM 2 Setup (Recommended)

1. **Install YubiHSM connector:**
```bash
wget https://developers.yubico.com/YubiHSM2/Releases/yubihsm2-sdk-2023.1-linux-amd64.tar.gz
tar -xzf yubihsm2-sdk-2023.1-linux-amd64.tar.gz
sudo dpkg -i yubihsm2-sdk/yubihsm2-*.deb
```

2. **Start YubiHSM connector:**
```bash
sudo systemctl enable yubihsm-connector
sudo systemctl start yubihsm-connector
```

3. **Generate authentication key:**
```bash
yubihsm-shell
yubihsm> connect
yubihsm> session open 1 password
yubihsm> generate authkey 2 "vault-auth" all password
yubihsm> quit
```

### AWS CloudHSM Setup

1. **Install CloudHSM client:**
```bash
wget https://s3.amazonaws.com/cloudhsmv2-software/CloudHsmClient/EL7/cloudhsm-client-latest.el7.x86_64.rpm
sudo yum install cloudhsm-client-latest.el7.x86_64.rpm
```

2. **Configure client:**
```bash
sudo /opt/cloudhsm/bin/configure -a <cluster-ip>
```

3. **Create crypto user:**
```bash
/opt/cloudhsm/bin/cloudhsm_mgmt_util
aws-cloudhsm> loginHSM PRECO admin password
aws-cloudhsm> createUser CU vault-user password
aws-cloudhsm> quit
```

## LDAP/AD Integration

### Active Directory Configuration

1. **Create service account:**
```powershell
New-ADUser -Name "vault-service" -UserPrincipalName "vault-service@company.com" -Path "OU=Service Accounts,DC=company,DC=com" -AccountPassword (ConvertTo-SecureString "secure_password" -AsPlainText -Force) -Enabled $true
```

2. **Grant permissions:**
```powershell
# Grant read permissions to user and group objects
dsacls "OU=Users,DC=company,DC=com" /G "vault-service@company.com:GR"
dsacls "OU=Groups,DC=company,DC=com" /G "vault-service@company.com:GR"
```

3. **Create security groups:**
```powershell
New-ADGroup -Name "Vault Admins" -GroupScope Global -Path "OU=Groups,DC=company,DC=com"
New-ADGroup -Name "Vault Users" -GroupScope Global -Path "OU=Groups,DC=company,DC=com"
```

### LDAP Configuration Testing

```bash
# Test LDAP connection
ldapsearch -H ldaps://ldap.company.com:636 -D "CN=vault-service,OU=Service Accounts,DC=company,DC=com" -W -b "DC=company,DC=com" "(sAMAccountName=testuser)"
```

## Monitoring and Logging

### Prometheus Configuration

Create `/etc/prometheus/vault.yml`:
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'vault-api'
    static_configs:
      - targets: ['localhost:9090']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

### Grafana Dashboard

Import the provided Grafana dashboard:
```bash
curl -X POST \
  http://grafana:3000/api/dashboards/db \
  -H 'Content-Type: application/json' \
  -d @monitoring/grafana-dashboard.json
```

### Log Aggregation

**ELK Stack Configuration:**

1. **Filebeat configuration:**
```yaml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/vault/*.log
  json.keys_under_root: true
  json.add_error_key: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "vault-logs-%{+yyyy.MM.dd}"
```

2. **Logstash configuration:**
```ruby
input {
  beats {
    port => 5044
  }
}

filter {
  if [fields][service] == "vault" {
    json {
      source => "message"
    }
    
    date {
      match => [ "timestamp", "ISO8601" ]
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "vault-logs-%{+yyyy.MM.dd}"
  }
}
```

## Backup and Recovery

### Database Backup

1. **Create backup script:**
```bash
#!/bin/bash
# /opt/vault/scripts/backup-database.sh

BACKUP_DIR="/var/backups/vault"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="vault_backup_${DATE}.sql.gz"

mkdir -p $BACKUP_DIR

pg_dump -h localhost -U vault -d vault | gzip > "${BACKUP_DIR}/${BACKUP_FILE}"

# Upload to S3
aws s3 cp "${BACKUP_DIR}/${BACKUP_FILE}" "s3://vault-backups-company/database/"

# Clean up local backups older than 7 days
find $BACKUP_DIR -name "vault_backup_*.sql.gz" -mtime +7 -delete
```

2. **Schedule backup:**
```bash
# Add to crontab
0 2 * * * /opt/vault/scripts/backup-database.sh
```

### Configuration Backup

```bash
#!/bin/bash
# /opt/vault/scripts/backup-config.sh

BACKUP_DIR="/var/backups/vault/config"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

tar -czf "${BACKUP_DIR}/config_backup_${DATE}.tar.gz" \
  /opt/vault/config/ \
  /etc/ssl/certs/vault.* \
  /etc/ssl/private/vault.*

# Upload to S3
aws s3 cp "${BACKUP_DIR}/config_backup_${DATE}.tar.gz" "s3://vault-backups-company/config/"
```

### Disaster Recovery

1. **Database restoration:**
```bash
# Stop vault services
sudo systemctl stop vault-api

# Restore database
gunzip -c vault_backup_20250825_020000.sql.gz | psql -h localhost -U vault -d vault

# Start vault services
sudo systemctl start vault-api
```

2. **Configuration restoration:**
```bash
# Extract configuration backup
tar -xzf config_backup_20250825_020000.tar.gz -C /

# Restart services
sudo systemctl restart vault-api
```

## High Availability

### Load Balancer Configuration (HAProxy)

Create `/etc/haproxy/haproxy.cfg`:
```
global
    daemon
    maxconn 4096
    ssl-default-bind-ciphers ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256
    ssl-default-bind-options no-sslv3 no-tlsv10 no-tlsv11

defaults
    mode http
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms
    option httplog

frontend vault_frontend
    bind *:443 ssl crt /etc/ssl/certs/vault.pem
    redirect scheme https if !{ ssl_fc }
    default_backend vault_backend

backend vault_backend
    balance roundrobin
    option httpchk GET /health
    server vault1 10.0.1.10:8080 check
    server vault2 10.0.1.11:8080 check
    server vault3 10.0.1.12:8080 check
```

### Database Clustering

**PostgreSQL Streaming Replication:**

1. **Primary server configuration:**
```sql
-- postgresql.conf
wal_level = replica
max_wal_senders = 3
wal_keep_segments = 64
archive_mode = on
archive_command = 'cp %p /var/lib/postgresql/archive/%f'

-- pg_hba.conf
host replication replica 10.0.1.0/24 md5
```

2. **Replica server setup:**
```bash
pg_basebackup -h primary-server -D /var/lib/postgresql/15/main -U replica -P -v -R -W
```

### Redis Clustering

```bash
# Create Redis cluster
redis-cli --cluster create \
  10.0.1.10:6379 10.0.1.11:6379 10.0.1.12:6379 \
  10.0.1.13:6379 10.0.1.14:6379 10.0.1.15:6379 \
  --cluster-replicas 1
```

## Performance Tuning

### Application Optimization

1. **Increase worker processes:**
```json
{
  "vault": {
    "api": {
      "workers": 16,
      "max_connections": 2000,
      "keepalive_timeout": 65
    }
  }
}
```

2. **Enable caching:**
```json
{
  "vault": {
    "performance": {
      "caching": {
        "enabled": true,
        "ttl_seconds": 600,
        "max_size_mb": 1024
      }
    }
  }
}
```

### Database Optimization

1. **PostgreSQL tuning:**
```sql
-- postgresql.conf
shared_buffers = 4GB
effective_cache_size = 12GB
work_mem = 16MB
maintenance_work_mem = 512MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
```

2. **Create indexes:**
```sql
CREATE INDEX CONCURRENTLY idx_credentials_organization_active 
ON credentials(organization_id) WHERE is_active = true;

CREATE INDEX CONCURRENTLY idx_audit_log_user_timestamp 
ON audit_log(user_id, timestamp DESC);

CREATE INDEX CONCURRENTLY idx_credentials_expires_at 
ON credentials(expires_at) WHERE expires_at IS NOT NULL;
```

### Redis Optimization

```
# redis.conf
maxmemory 8gb
maxmemory-policy allkeys-lru
tcp-keepalive 300
timeout 0
tcp-backlog 511
```

## Security Hardening

### System Hardening

1. **Disable unnecessary services:**
```bash
sudo systemctl disable cups
sudo systemctl disable avahi-daemon
sudo systemctl disable bluetooth
```

2. **Configure fail2ban:**
```ini
# /etc/fail2ban/jail.local
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3

[vault-api]
enabled = true
port = 8080
logpath = /var/log/vault/vault.log
maxretry = 5
```

3. **Set up intrusion detection:**
```bash
# Install AIDE
sudo apt-get install aide
sudo aideinit
sudo mv /var/lib/aide/aide.db.new /var/lib/aide/aide.db

# Schedule daily checks
echo "0 3 * * * /usr/bin/aide --check" | sudo crontab -
```

### Network Security

1. **Configure iptables:**
```bash
#!/bin/bash
# Flush existing rules
iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X

# Default policies
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# Allow loopback
iptables -A INPUT -i lo -j ACCEPT

# Allow established connections
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow SSH
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# Allow HTTPS
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Allow API port from internal networks
iptables -A INPUT -p tcp --dport 8080 -s 10.0.0.0/8 -j ACCEPT
iptables -A INPUT -p tcp --dport 8080 -s 172.16.0.0/12 -j ACCEPT
iptables -A INPUT -p tcp --dport 8080 -s 192.168.0.0/16 -j ACCEPT

# Save rules
iptables-save > /etc/iptables/rules.v4
```

2. **Configure network segmentation:**
```bash
# Create separate VLANs for different tiers
# Database VLAN: 10.1.0.0/24
# Application VLAN: 10.2.0.0/24
# Management VLAN: 10.3.0.0/24
```

## Troubleshooting

### Common Issues

1. **Database connection errors:**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check connections
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"

# Check logs
sudo tail -f /var/log/postgresql/postgresql-15-main.log
```

2. **Redis connection errors:**
```bash
# Check Redis status
sudo systemctl status redis

# Test connection
redis-cli ping

# Check logs
sudo tail -f /var/log/redis/redis-server.log
```

3. **SSL/TLS certificate issues:**
```bash
# Check certificate validity
openssl x509 -in /etc/ssl/certs/vault.crt -text -noout

# Test SSL connection
openssl s_client -connect vault.company.com:443
```

4. **HSM connectivity issues:**
```bash
# YubiHSM 2
yubihsm-shell -a connector=http://localhost:12345
yubihsm> connect
yubihsm> session open 1 password
yubihsm> list objects

# AWS CloudHSM
/opt/cloudhsm/bin/cloudhsm_mgmt_util
aws-cloudhsm> info server
```

### Log Analysis

1. **Application logs:**
```bash
# View real-time logs
sudo tail -f /var/log/vault/vault.log

# Search for errors
sudo grep -i error /var/log/vault/vault.log

# Analyze authentication failures
sudo grep "auth_failure" /var/log/vault/vault.log | tail -20
```

2. **System logs:**
```bash
# Check system messages
sudo journalctl -u vault-api -f

# Check for security events
sudo grep "vault" /var/log/auth.log
```

### Performance Diagnostics

1. **Database performance:**
```sql
-- Check slow queries
SELECT query, mean_time, calls, total_time 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- Check connection usage
SELECT count(*), state 
FROM pg_stat_activity 
GROUP BY state;
```

2. **Redis performance:**
```bash
# Monitor Redis
redis-cli monitor

# Check memory usage
redis-cli info memory

# Check slow queries
redis-cli slowlog get 10
```

## Maintenance

### Regular Maintenance Tasks

1. **Daily tasks:**
   - Check system health
   - Review security alerts
   - Monitor backup completion
   - Check disk space usage

2. **Weekly tasks:**
   - Review audit logs
   - Update security patches
   - Check certificate expiration
   - Performance monitoring review

3. **Monthly tasks:**
   - Compliance report generation
   - Security assessment
   - Capacity planning review
   - Disaster recovery testing

4. **Quarterly tasks:**
   - Full security audit
   - Penetration testing
   - Business continuity testing
   - Configuration review

### Update Procedures

1. **Application updates:**
```bash
# Backup current version
sudo cp -r /opt/vault /opt/vault.backup

# Download new version
wget https://releases.haivemind.com/vault/v1.1.0/vault-v1.1.0.tar.gz

# Extract and deploy
tar -xzf vault-v1.1.0.tar.gz
sudo cp -r vault-v1.1.0/* /opt/vault/

# Run database migrations
python /opt/vault/scripts/migrate.py

# Restart services
sudo systemctl restart vault-api
```

2. **Security updates:**
```bash
# Update system packages
sudo apt-get update && sudo apt-get upgrade

# Update Python dependencies
pip install -r requirements.txt --upgrade

# Update SSL certificates
certbot renew
```

### Health Checks

Create `/opt/vault/scripts/health-check.sh`:
```bash
#!/bin/bash

# Check API health
curl -f http://localhost:8080/health || exit 1

# Check database connectivity
pg_isready -h localhost -p 5432 -U vault || exit 1

# Check Redis connectivity
redis-cli ping || exit 1

# Check disk space
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "Disk usage is above 80%"
    exit 1
fi

echo "All health checks passed"
```

---

## Support and Documentation

For additional support and documentation:

- **Technical Support:** support@unit221b.com
- **Security Issues:** security@unit221b.com
- **Documentation:** https://docs.haivemind.com/vault
- **Community:** https://community.haivemind.com

---

**Document Classification:** Internal Use  
**Review Cycle:** Quarterly  
**Next Review:** 2025-11-25  
**Approved By:** Lance James, Chief Technology Officer