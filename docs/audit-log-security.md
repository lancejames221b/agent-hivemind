# Vault Audit Log Security

**Priority:** P0 (Critical Security)
**Author:** Lance James, Unit 221B
**Last Updated:** 2025-11-26

---

## Overview

The Vault audit logging system tracks all credential operations for security, compliance, and forensic purposes. This document defines what data IS logged vs what is REDACTED to ensure no sensitive credential information is ever stored in audit logs.

**Security Principle:** Audit logs must contain only metadata. Never log credential data, passwords, API keys, or encryption artifacts.

---

## What IS Logged (Safe Metadata)

### ✅ Credential Metadata
- `credential_id` (UUID)
- `credential_type` (enum: "password", "api_key", "certificate", "ssh_key", etc.)
- `name` (credential display name)
- `description` (credential description)
- `environment` (production, staging, development)
- `service` (database, api, external_service)
- `project` (project identifier)
- `tags` (list of tags)

### ✅ Audit Metadata
- `audit_id` (UUID)
- `user_id` (performing user)
- `action` ("store_credential", "retrieve_credential", "rotate_credential", etc.)
- `timestamp` (operation time)
- `success` (boolean)
- `ip_address` (source IP)
- `user_agent` (client user agent)
- `session_id` (session identifier)
- `request_id` (request tracking ID)

### ✅ Access Control
- `access_level` (enum: "viewer", "editor", "admin")
- `target_user` (user being granted/revoked access)
- `denial_reason` ("insufficient_permissions", "mfa_required", etc.)

### ✅ Rotation Metadata
- `rotation_method` ("manual", "automatic", "scheduled")
- `previous_version` (integer version number)
- `new_version` (integer version number)
- `rotation_reason` (business justification)

### ✅ Error Information
- `error` (exception message)
- Error messages do NOT contain credential values
- Stack traces are logged separately, not in audit logs

---

## What is NEVER Logged (Sensitive Data)

### ❌ Credential Data
- **credential_data** (Dict[str, Any] containing passwords, keys, secrets)
- Plaintext passwords
- API keys and tokens
- SSL/TLS certificates and private keys
- SSH keys (public or private)
- Database credentials
- OAuth tokens and refresh tokens
- Webhook secrets
- Service account credentials

### ❌ Encryption Artifacts
- **encrypted_data** (encrypted credential blob)
- **master_password** (used to decrypt credentials)
- **encryption_key** (derived encryption key)
- **salt** (cryptographic salt bytes)
- **nonce** (initialization vector bytes)
- **tag** (authentication tag)
- Key derivation parameters (beyond algorithm name)

### ❌ Decrypted Values
- Decrypted passwords
- Decrypted API keys
- Decrypted secrets of any kind
- Plain-text credential fields after decryption

---

## Code Patterns

### ✅ SAFE: Store Credential Audit
```python
# src/vault/core_vault.py:395-396
await self._log_audit_event(
    user_id,
    metadata.credential_id,
    "store_credential",
    {
        "credential_type": metadata.credential_type.value,  # ✅ Safe: enum value
        "environment": metadata.environment,                  # ✅ Safe: metadata
        "service": metadata.service                           # ✅ Safe: metadata
        # ❌ DO NOT ADD: "credential_data": credential_data
    },
    True
)
```

**Why Safe:**
- Only logs credential type, environment, service (metadata)
- Does NOT log the actual credential data
- Safe for long-term retention and security team access

---

### ✅ SAFE: Retrieve Credential Audit
```python
# src/vault/core_vault.py:489-490
# Decryption happens here:
credential_data = self.decrypt_credential_data(encrypted_cred, master_password)

# Audit logging happens here (AFTER decryption):
await self._log_audit_event(
    user_id,
    credential_id,
    "retrieve_credential",
    {
        "credential_type": metadata.credential_type.value  # ✅ Safe: metadata only
        # ❌ DO NOT ADD: "credential_data": credential_data
        # ❌ DO NOT ADD: "decrypted_data": credential_data
    },
    True
)
```

**Why Safe:**
- Decrypted credential data is in scope but is NOT passed to audit function
- Only credential type (metadata) is logged
- Decrypted values remain in memory only, never persisted to audit log

---

### ✅ SAFE: Rotate Credential Audit
```python
# src/vault/vault_dashboard_api.py:602-613
await audit_manager.log_event(
    AuditEventType.CREDENTIAL_ROTATED,
    user_id=current_user['id'],
    ip_address=req.client.host,
    resource_id=credential_id,
    resource_name=credential['name'],
    metadata={
        'rotation_method': rotation_result.get('method', 'manual'),  # ✅ Safe
        'previous_version': rotation_result.get('previous_version'),  # ✅ Safe
        'new_version': rotation_result.get('new_version')             # ✅ Safe
        # ❌ DO NOT ADD: 'old_credential': old_cred
        # ❌ DO NOT ADD: 'new_credential': new_cred
    }
)
```

**Why Safe:**
- Logs rotation method and version numbers (metadata)
- Does NOT log old or new credential values
- Version numbers are integers, safe for auditing

---

### ❌ UNSAFE: Do NOT Do This
```python
# NEVER DO THIS - SECURITY VIOLATION
await self._log_audit_event(
    user_id,
    credential_id,
    "retrieve_credential",
    {
        "credential_type": "password",
        "credential_data": {                    # ❌ SECURITY VIOLATION
            "password": "supersecret123",      # ❌ NEVER LOG THIS
            "username": "admin"                # ❌ EVEN THIS IS RISKY
        }
    },
    True
)
```

**Why Unsafe:**
- Logs plaintext password in audit log database
- Audit logs may be backed up to less secure systems
- Audit logs are readable by security team
- Audit logs retained longer than credentials are valid
- Defeats entire purpose of encrypted credential vault

---

## Implementation Details

### Audit Log Database Schema
```sql
CREATE TABLE vault_audit_log (
    audit_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    credential_id TEXT,
    action TEXT NOT NULL,
    details TEXT,              -- JSON-serialized metadata (NO CREDENTIALS)
    ip_address TEXT,
    user_agent TEXT,
    timestamp TIMESTAMP NOT NULL,
    success BOOLEAN NOT NULL
);
```

**Storage Format:**
- `details` column contains JSON-serialized dictionary
- JSON is plaintext-readable in database
- Database may be backed up, replicated, archived
- Therefore: NEVER put sensitive data in `details`

---

### Core Audit Function
```python
# src/vault/core_vault.py:641-663
async def _log_audit_event(
    self,
    user_id: str,
    credential_id: Optional[str],
    action: str,
    details: Dict[str, Any],  # ⚠️ CALLER MUST SANITIZE
    success: bool,
    ip_address: str = None,
    user_agent: str = None
):
    """Log audit event - details dict MUST NOT contain credential data"""
    audit_id = secrets.token_urlsafe(32)

    with sqlite3.connect(self.db_path) as conn:
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO vault_audit_log
            (audit_id, user_id, credential_id, action, details, ip_address, user_agent, timestamp, success)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            audit_id, user_id, credential_id, action,
            json.dumps(details),  # ⚠️ Serializes to plaintext JSON
            ip_address, user_agent, datetime.utcnow(), success
        ))

        conn.commit()
```

**Security Notes:**
- `details` parameter is caller's responsibility to sanitize
- `json.dumps(details)` creates plaintext JSON
- All callers reviewed: NONE pass credential data ✅
- Function itself does not filter or redact

---

## Testing

### Security Test Suite
Location: `tests/security/test_audit_security.py`

**Test Coverage:**
- ✅ store_credential: No credential_data logged
- ✅ retrieve_credential: No decrypted data logged
- ✅ rotate_credential: No old/new credentials logged
- ✅ grant_access: No credential data logged
- ✅ Encryption artifacts: No salt/nonce/keys logged
- ✅ Comprehensive review: All operations verified secure

**Run Tests:**
```bash
python3 tests/security/test_audit_security.py
```

**Expected Output:**
```
✅ ALL TESTS PASSED - AUDIT LOGGING IS SECURE
No sensitive credential data found in audit logs
```

---

## Compliance and Audit Log Access

### Who Can Access Audit Logs

**Approved Access:**
- Security team (read-only)
- Compliance auditors (read-only)
- Incident response team (read-only)
- System administrators (read-only)

**Access Control:**
- Audit logs should be separate database or table
- Restricted permissions (not world-readable)
- Accessed via API with authentication
- All audit log access should itself be audited

### Retention Policy

**Default Retention:** 365 days (configurable)

**Rationale:**
- Audit logs contain NO sensitive credential data
- Safe for long-term retention
- Useful for forensic analysis
- Compliance requirements (SOX, HIPAA, PCI-DSS)

### Backup and Archival

**Safe to Backup:**
- Audit logs can be backed up to less secure systems
- No credential data risk
- Archive to cold storage after retention period

**Not Safe to Backup:**
- Encrypted credentials database (needs same security as primary)
- Master passwords (should never be stored)
- Encryption keys (use HSM or key management service)

---

## Code Review Checklist

When reviewing code that touches audit logging:

- [ ] Verify `details` dict contains only metadata
- [ ] Verify no `credential_data` passed to audit function
- [ ] Verify no decrypted values in `details`
- [ ] Verify no encryption artifacts (salt, nonce, keys)
- [ ] Verify error messages do not contain credential values
- [ ] Add test case to `test_audit_security.py`
- [ ] Run full test suite before merge

---

## Security Testing

### Manual Audit Log Review
```bash
# Connect to audit database
sqlite3 data/vault.db

# Query audit logs
SELECT audit_id, user_id, action, details, timestamp
FROM vault_audit_log
ORDER BY timestamp DESC
LIMIT 10;

# Search for suspicious patterns (should return 0 rows)
SELECT * FROM vault_audit_log WHERE details LIKE '%password%';
SELECT * FROM vault_audit_log WHERE details LIKE '%secret%';
SELECT * FROM vault_audit_log WHERE details LIKE '%credential_data%';
```

### Automated Scanning
```bash
# Scan audit log database for sensitive patterns
grep -i "password\|secret\|credential_data" data/vault.db && echo "❌ SECURITY ISSUE" || echo "✅ Clean"
```

---

## Incident Response

### If Credential Data is Found in Audit Log

**Severity:** P0 (Critical Security Incident)

**Immediate Actions:**
1. Stop all audit logging (prevent further leakage)
2. Identify which credentials were leaked
3. Rotate ALL affected credentials immediately
4. Identify root cause (which code path logged the data)
5. Delete or redact audit log entries with sensitive data
6. Review all audit log backups and archives
7. Notify security team and affected users

**Fix and Prevention:**
1. Fix the code path that leaked data
2. Add test case to prevent regression
3. Run full security test suite
4. Code review all audit logging changes
5. Document incident and lessons learned

---

## References

- **Code:** `src/vault/core_vault.py:641-663` (_log_audit_event)
- **Code:** `src/vault/audit_manager.py:527-574` (log_event)
- **Tests:** `tests/security/test_audit_security.py`
- **Review:** `AUDIT_REVIEW.md` (comprehensive security review)

---

## Summary

**Audit Logging Security Principles:**

1. ✅ **Log metadata only:** credential_id, type, environment, timestamps
2. ❌ **Never log credential data:** passwords, API keys, secrets
3. ❌ **Never log encryption artifacts:** salt, nonce, keys
4. ❌ **Never log decrypted values:** even temporarily decrypted data
5. ✅ **Safe for long-term retention:** audit logs contain no sensitive data
6. ✅ **Testable security:** comprehensive test suite verifies no leaks

**Security Status:** ✅ VERIFIED SECURE (2025-11-26)

All audit logging reviewed. No credential data logged. Safe for production use.
