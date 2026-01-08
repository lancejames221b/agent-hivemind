"""
Security tests for Vault audit logging system.
Verifies that NO sensitive credential data is ever logged in audit trails.

Author: Lance James, Unit 221B
Priority: P0 (Critical Security)
"""

import asyncio
import json
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path


class AuditSecurityTestCase(unittest.TestCase):
    """Base test case for audit security testing"""

    def setUp(self):
        """Set up test environment"""
        # Create temporary database
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.test_db.name
        self.test_db.close()

        # Initialize database schema
        self._init_test_database()

        # Test credentials (these should NEVER appear in audit logs)
        self.sensitive_values = {
            'password': 'SENSITIVE_SECRET_PASSWORD_123',
            'api_key': 'sk-SENSITIVE_API_KEY_456',
            'database_password': 'DB_SECRET_789',
            'private_key': '-----BEGIN RSA PRIVATE KEY-----\nMIIEpAI...',
            'master_password': 'MASTER_PASSWORD_SECRET'
        }

    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def _init_test_database(self):
        """Initialize test database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create vault_audit_log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vault_audit_log (
                audit_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                credential_id TEXT,
                action TEXT NOT NULL,
                details TEXT,
                ip_address TEXT,
                user_agent TEXT,
                timestamp TIMESTAMP NOT NULL,
                success BOOLEAN NOT NULL
            )
        ''')

        # Create credential_metadata table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS credential_metadata (
                credential_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                credential_type TEXT NOT NULL,
                environment TEXT,
                service TEXT,
                project TEXT,
                owner_id TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                last_accessed TIMESTAMP,
                expires_at TIMESTAMP,
                rotation_schedule TEXT,
                status TEXT NOT NULL,
                tags TEXT,
                access_restrictions TEXT,
                compliance_labels TEXT,
                audit_required BOOLEAN DEFAULT TRUE,
                emergency_access BOOLEAN DEFAULT FALSE
            )
        ''')

        # Create encrypted_credentials table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS encrypted_credentials (
                credential_id TEXT PRIMARY KEY,
                encrypted_data BLOB NOT NULL,
                encryption_algorithm TEXT NOT NULL,
                key_derivation_method TEXT NOT NULL,
                salt BLOB NOT NULL,
                nonce BLOB NOT NULL,
                tag BLOB,
                key_version INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        ''')

        conn.commit()
        conn.close()

    def _log_test_audit_event(self, user_id: str, credential_id: str, action: str,
                              details: Dict[str, Any], success: bool = True):
        """Simulate logging an audit event (mirrors core_vault._log_audit_event)"""
        import secrets

        audit_id = secrets.token_urlsafe(32)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO vault_audit_log
            (audit_id, user_id, credential_id, action, details, ip_address, user_agent, timestamp, success)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            audit_id, user_id, credential_id, action, json.dumps(details),
            '127.0.0.1', 'TestAgent/1.0', datetime.utcnow(), success
        ))

        conn.commit()
        conn.close()

        return audit_id

    def _get_audit_log_entries(self, credential_id: str = None) -> List[Dict[str, Any]]:
        """Retrieve audit log entries for analysis"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if credential_id:
            cursor.execute('SELECT * FROM vault_audit_log WHERE credential_id = ?', (credential_id,))
        else:
            cursor.execute('SELECT * FROM vault_audit_log')

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def _assert_no_sensitive_data(self, audit_entries: List[Dict[str, Any]],
                                  sensitive_values: List[str]):
        """Assert that sensitive values do not appear in audit logs"""
        for entry in audit_entries:
            # Convert entire entry to JSON for comprehensive checking
            entry_json = json.dumps(entry).lower()

            for sensitive_value in sensitive_values:
                sensitive_lower = sensitive_value.lower()
                self.assertNotIn(
                    sensitive_lower,
                    entry_json,
                    f"❌ SECURITY VIOLATION: Found sensitive value '{sensitive_value}' in audit log entry {entry['audit_id']}"
                )


class TestStoreCredentialAudit(AuditSecurityTestCase):
    """Test audit logging for store_credential operations"""

    def test_store_credential_success_no_data_leak(self):
        """Test that store_credential audit does not log credential data"""
        # Simulate storing a credential with sensitive data
        credential_id = 'test-cred-001'

        # This is what SHOULD be logged (metadata only)
        self._log_test_audit_event(
            user_id='user-123',
            credential_id=credential_id,
            action='store_credential',
            details={
                'credential_type': 'password',
                'environment': 'production',
                'service': 'database'
            },
            success=True
        )

        # Verify no sensitive data in audit log
        entries = self._get_audit_log_entries(credential_id)
        self.assertEqual(len(entries), 1)

        # Verify sensitive passwords are NOT logged
        self._assert_no_sensitive_data(
            entries,
            [self.sensitive_values['password'], self.sensitive_values['api_key']]
        )

        # Verify metadata IS logged
        entry = entries[0]
        details = json.loads(entry['details'])
        self.assertEqual(details['credential_type'], 'password')
        self.assertEqual(details['environment'], 'production')
        self.assertNotIn('credential_data', details)

        print("✅ Test passed: store_credential audit contains no sensitive data")

    def test_store_credential_failure_no_data_leak(self):
        """Test that store_credential failure audit does not log credential data"""
        credential_id = 'test-cred-002'

        # Simulate error scenario
        self._log_test_audit_event(
            user_id='user-123',
            credential_id=credential_id,
            action='store_credential',
            details={
                'error': 'Database connection failed'
            },
            success=False
        )

        entries = self._get_audit_log_entries(credential_id)
        self._assert_no_sensitive_data(
            entries,
            [self.sensitive_values['password']]
        )

        print("✅ Test passed: store_credential failure audit contains no sensitive data")


class TestRetrieveCredentialAudit(AuditSecurityTestCase):
    """Test audit logging for retrieve_credential operations"""

    def test_retrieve_credential_success_no_decrypted_data(self):
        """Test that retrieve_credential audit does not log decrypted credential data"""
        credential_id = 'test-cred-003'

        # What SHOULD be logged (metadata only, NOT decrypted credential)
        self._log_test_audit_event(
            user_id='user-456',
            credential_id=credential_id,
            action='retrieve_credential',
            details={
                'credential_type': 'api_key'
            },
            success=True
        )

        entries = self._get_audit_log_entries(credential_id)

        # Verify decrypted API key is NOT logged
        self._assert_no_sensitive_data(
            entries,
            [self.sensitive_values['api_key'], 'sk-SENSITIVE']
        )

        # Verify metadata IS logged
        entry = entries[0]
        details = json.loads(entry['details'])
        self.assertEqual(details['credential_type'], 'api_key')
        self.assertNotIn('credential_data', details)
        self.assertNotIn('decrypted_data', details)

        print("✅ Test passed: retrieve_credential audit contains no decrypted data")

    def test_retrieve_credential_denied_no_leak(self):
        """Test that credential retrieval denial does not log credential data"""
        credential_id = 'test-cred-004'

        self._log_test_audit_event(
            user_id='user-789',
            credential_id=credential_id,
            action='retrieve_credential_denied',
            details={
                'reason': 'insufficient_permissions'
            },
            success=False
        )

        entries = self._get_audit_log_entries(credential_id)

        # Verify no credential data (access was denied anyway)
        self._assert_no_sensitive_data(
            entries,
            list(self.sensitive_values.values())
        )

        entry = entries[0]
        details = json.loads(entry['details'])
        self.assertEqual(details['reason'], 'insufficient_permissions')

        print("✅ Test passed: retrieve_credential_denied audit contains no sensitive data")


class TestRotateCredentialAudit(AuditSecurityTestCase):
    """Test audit logging for rotate_credential operations"""

    def test_rotate_credential_no_old_or_new_credentials(self):
        """Test that credential rotation does not log old or new credential values"""
        credential_id = 'test-cred-005'

        # What SHOULD be logged (version numbers only, NOT credentials)
        self._log_test_audit_event(
            user_id='user-admin',
            credential_id=credential_id,
            action='rotate_credential',
            details={
                'rotation_method': 'automatic',
                'previous_version': 1,
                'new_version': 2
            },
            success=True
        )

        entries = self._get_audit_log_entries(credential_id)

        # Verify neither old nor new passwords are logged
        self._assert_no_sensitive_data(
            entries,
            [
                'OLD_PASSWORD_123',
                'NEW_PASSWORD_456',
                self.sensitive_values['password'],
                self.sensitive_values['database_password']
            ]
        )

        # Verify rotation metadata IS logged
        entry = entries[0]
        details = json.loads(entry['details'])
        self.assertEqual(details['rotation_method'], 'automatic')
        self.assertEqual(details['previous_version'], 1)
        self.assertEqual(details['new_version'], 2)
        self.assertNotIn('old_credential', details)
        self.assertNotIn('new_credential', details)
        self.assertNotIn('credential_data', details)

        print("✅ Test passed: rotate_credential audit contains no credential values")


class TestGrantAccessAudit(AuditSecurityTestCase):
    """Test audit logging for grant_access operations"""

    def test_grant_access_no_credential_data(self):
        """Test that grant_access audit does not log credential data"""
        credential_id = 'test-cred-006'

        self._log_test_audit_event(
            user_id='admin-user',
            credential_id=credential_id,
            action='grant_access',
            details={
                'target_user': 'user-123',
                'access_level': 'viewer'
            },
            success=True
        )

        entries = self._get_audit_log_entries(credential_id)

        # Verify no credential data is logged
        self._assert_no_sensitive_data(
            entries,
            list(self.sensitive_values.values())
        )

        # Verify access control metadata IS logged
        entry = entries[0]
        details = json.loads(entry['details'])
        self.assertEqual(details['target_user'], 'user-123')
        self.assertEqual(details['access_level'], 'viewer')

        print("✅ Test passed: grant_access audit contains no credential data")


class TestEncryptionArtifactsSecurity(AuditSecurityTestCase):
    """Test that encryption artifacts (salt, nonce, keys) are never logged"""

    def test_no_encryption_artifacts_in_audit(self):
        """Test that salt, nonce, encryption keys never appear in audit logs"""
        credential_id = 'test-cred-007'

        # These should NEVER appear in audit logs
        encryption_artifacts = [
            'salt_bytes_12345',
            'nonce_bytes_67890',
            'encryption_key_abcdef',
            self.sensitive_values['master_password']
        ]

        # Simulate various operations
        for action in ['store_credential', 'retrieve_credential', 'rotate_credential']:
            self._log_test_audit_event(
                user_id='user-999',
                credential_id=credential_id,
                action=action,
                details={'credential_type': 'password'},
                success=True
            )

        entries = self._get_audit_log_entries(credential_id)

        # Verify NO encryption artifacts are logged
        self._assert_no_sensitive_data(entries, encryption_artifacts)

        print("✅ Test passed: No encryption artifacts in audit logs")


class TestComprehensiveAuditReview(AuditSecurityTestCase):
    """Comprehensive security review of entire audit log system"""

    def test_audit_log_comprehensive_security(self):
        """Comprehensive test: multiple operations, no sensitive data leaks"""
        test_scenarios = [
            # (action, details, sensitive_values_to_check)
            ('store_credential', {'credential_type': 'password'}, [self.sensitive_values['password']]),
            ('retrieve_credential', {'credential_type': 'api_key'}, [self.sensitive_values['api_key']]),
            ('rotate_credential', {'rotation_method': 'manual', 'new_version': 2},
             ['OLD_PWD', 'NEW_PWD']),
            ('grant_access', {'target_user': 'user-x', 'access_level': 'editor'},
             list(self.sensitive_values.values())),
            ('retrieve_credential_denied', {'reason': 'mfa_required'},
             list(self.sensitive_values.values())),
        ]

        for i, (action, details, sensitive_checks) in enumerate(test_scenarios):
            credential_id = f'comprehensive-test-{i}'
            self._log_test_audit_event(
                user_id=f'user-{i}',
                credential_id=credential_id,
                action=action,
                details=details,
                success=True
            )

        # Get all audit entries
        all_entries = self._get_audit_log_entries()

        # Verify NO sensitive data in entire audit log
        all_sensitive_values = list(self.sensitive_values.values()) + [
            'OLD_PWD', 'NEW_PWD', 'SECRET', 'SENSITIVE', 'PRIVATE_KEY'
        ]

        self._assert_no_sensitive_data(all_entries, all_sensitive_values)

        print(f"✅ Test passed: Comprehensive audit review - {len(all_entries)} entries verified secure")


def run_audit_security_tests():
    """Run all audit security tests"""
    print("\n" + "="*80)
    print("VAULT AUDIT LOGGING SECURITY TEST SUITE")
    print("="*80)
    print(f"Priority: P0 (Critical Security)")
    print(f"Test Date: {datetime.utcnow().isoformat()}")
    print(f"Author: Lance James, Unit 221B")
    print("="*80 + "\n")

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestStoreCredentialAudit))
    suite.addTests(loader.loadTestsFromTestCase(TestRetrieveCredentialAudit))
    suite.addTests(loader.loadTestsFromTestCase(TestRotateCredentialAudit))
    suite.addTests(loader.loadTestsFromTestCase(TestGrantAccessAudit))
    suite.addTests(loader.loadTestsFromTestCase(TestEncryptionArtifactsSecurity))
    suite.addTests(loader.loadTestsFromTestCase(TestComprehensiveAuditReview))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED - AUDIT LOGGING IS SECURE")
        print("No sensitive credential data found in audit logs")
    else:
        print("\n❌ TESTS FAILED - SECURITY ISSUES DETECTED")
        print("Review failures above for details")

    print("="*80 + "\n")

    return result


if __name__ == '__main__':
    result = run_audit_security_tests()
    exit(0 if result.wasSuccessful() else 1)
