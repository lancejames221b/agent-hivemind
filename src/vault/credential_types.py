"""
Comprehensive Credential Types Support
Handles different types of credentials with validation and specialized operations.

Author: Lance James, Unit 221B
"""

import asyncio
import logging
import json
import re
import base64
import secrets
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import ipaddress
from urllib.parse import urlparse

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, ec, ed25519
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID


class CredentialType(Enum):
    """Supported credential types"""
    PASSWORD = "password"
    API_KEY = "api_key"
    SSH_KEY = "ssh_key"
    CERTIFICATE = "certificate"
    DATABASE_CONNECTION = "database_connection"
    OAUTH_CREDENTIALS = "oauth_credentials"
    CLOUD_CREDENTIALS = "cloud_credentials"
    WEBHOOK_SECRET = "webhook_secret"
    ENCRYPTION_KEY = "encryption_key"
    SIGNING_KEY = "signing_key"
    TOTP_SECRET = "totp_secret"
    RECOVERY_CODES = "recovery_codes"
    BEARER_TOKEN = "bearer_token"
    CUSTOM = "custom"


class PasswordStrength(Enum):
    """Password strength levels"""
    WEAK = "weak"
    FAIR = "fair"
    GOOD = "good"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


class KeyType(Enum):
    """Cryptographic key types"""
    RSA_2048 = "rsa_2048"
    RSA_4096 = "rsa_4096"
    ECDSA_P256 = "ecdsa_p256"
    ECDSA_P384 = "ecdsa_p384"
    ED25519 = "ed25519"
    AES_256 = "aes_256"
    CHACHA20 = "chacha20"


@dataclass
class ValidationResult:
    """Credential validation result"""
    is_valid: bool
    strength_score: float  # 0.0 to 1.0
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CredentialData:
    """Base credential data structure"""
    credential_type: CredentialType
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'credential_type': self.credential_type.value,
            'data': self.data,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CredentialData':
        """Create from dictionary"""
        return cls(
            credential_type=CredentialType(data['credential_type']),
            data=data['data'],
            metadata=data.get('metadata', {}),
            created_at=datetime.fromisoformat(data['created_at']),
            expires_at=datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None
        )


class CredentialValidator(ABC):
    """Abstract base class for credential validators"""
    
    @abstractmethod
    async def validate(self, credential_data: CredentialData) -> ValidationResult:
        """Validate credential data"""
        pass
    
    @abstractmethod
    def get_strength_requirements(self) -> Dict[str, Any]:
        """Get strength requirements for this credential type"""
        pass


class PasswordValidator(CredentialValidator):
    """Password credential validator"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get('password_policy', {})
        self.min_length = self.config.get('min_length', 12)
        self.require_uppercase = self.config.get('require_uppercase', True)
        self.require_lowercase = self.config.get('require_lowercase', True)
        self.require_digits = self.config.get('require_digits', True)
        self.require_special = self.config.get('require_special', True)
        self.forbidden_patterns = self.config.get('forbidden_patterns', [])
        self.common_passwords_file = self.config.get('common_passwords_file')
        
        # Load common passwords if file provided
        self.common_passwords = set()
        if self.common_passwords_file:
            try:
                with open(self.common_passwords_file, 'r') as f:
                    self.common_passwords = {line.strip().lower() for line in f}
            except Exception:
                pass
    
    async def validate(self, credential_data: CredentialData) -> ValidationResult:
        """Validate password credential"""
        password = credential_data.data.get('password', '')
        username = credential_data.data.get('username', '')
        
        issues = []
        recommendations = []
        strength_score = 0.0
        
        # Length check
        if len(password) < self.min_length:
            issues.append(f"Password must be at least {self.min_length} characters long")
        else:
            strength_score += 0.2
        
        # Character class checks
        has_upper = bool(re.search(r'[A-Z]', password))
        has_lower = bool(re.search(r'[a-z]', password))
        has_digit = bool(re.search(r'\d', password))
        has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
        
        if self.require_uppercase and not has_upper:
            issues.append("Password must contain uppercase letters")
        elif has_upper:
            strength_score += 0.15
        
        if self.require_lowercase and not has_lower:
            issues.append("Password must contain lowercase letters")
        elif has_lower:
            strength_score += 0.15
        
        if self.require_digits and not has_digit:
            issues.append("Password must contain digits")
        elif has_digit:
            strength_score += 0.15
        
        if self.require_special and not has_special:
            issues.append("Password must contain special characters")
        elif has_special:
            strength_score += 0.15
        
        # Entropy calculation
        entropy = self._calculate_entropy(password)
        if entropy < 50:
            issues.append("Password has low entropy")
            recommendations.append("Use a longer password with more varied characters")
        else:
            strength_score += min(0.2, entropy / 100)
        
        # Common password check
        if password.lower() in self.common_passwords:
            issues.append("Password is commonly used")
            recommendations.append("Choose a unique password")
            strength_score *= 0.5
        
        # Username similarity check
        if username and self._is_similar_to_username(password, username):
            issues.append("Password is too similar to username")
            recommendations.append("Use a password unrelated to your username")
            strength_score *= 0.7
        
        # Pattern checks
        for pattern in self.forbidden_patterns:
            if re.search(pattern, password, re.IGNORECASE):
                issues.append(f"Password contains forbidden pattern")
                strength_score *= 0.8
        
        # Additional recommendations
        if len(password) < 16:
            recommendations.append("Consider using a longer password (16+ characters)")
        
        if not self._has_mixed_case(password):
            recommendations.append("Mix uppercase and lowercase letters")
        
        return ValidationResult(
            is_valid=len(issues) == 0,
            strength_score=min(1.0, strength_score),
            issues=issues,
            recommendations=recommendations,
            metadata={
                'entropy': entropy,
                'length': len(password),
                'character_classes': sum([has_upper, has_lower, has_digit, has_special])
            }
        )
    
    def _calculate_entropy(self, password: str) -> float:
        """Calculate password entropy"""
        if not password:
            return 0.0
        
        # Character space size
        charset_size = 0
        if re.search(r'[a-z]', password):
            charset_size += 26
        if re.search(r'[A-Z]', password):
            charset_size += 26
        if re.search(r'\d', password):
            charset_size += 10
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            charset_size += 32
        
        # Entropy = log2(charset_size^length)
        import math
        return len(password) * math.log2(charset_size) if charset_size > 0 else 0.0
    
    def _is_similar_to_username(self, password: str, username: str) -> bool:
        """Check if password is similar to username"""
        if len(username) < 3:
            return False
        
        password_lower = password.lower()
        username_lower = username.lower()
        
        # Direct substring check
        if username_lower in password_lower or password_lower in username_lower:
            return True
        
        # Levenshtein distance check for similarity
        return self._levenshtein_distance(password_lower, username_lower) < max(3, len(username) // 3)
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def _has_mixed_case(self, password: str) -> bool:
        """Check if password has mixed case"""
        return any(c.isupper() for c in password) and any(c.islower() for c in password)
    
    def get_strength_requirements(self) -> Dict[str, Any]:
        """Get password strength requirements"""
        return {
            'min_length': self.min_length,
            'require_uppercase': self.require_uppercase,
            'require_lowercase': self.require_lowercase,
            'require_digits': self.require_digits,
            'require_special': self.require_special,
            'min_entropy': 50
        }


class APIKeyValidator(CredentialValidator):
    """API key credential validator"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get('api_key_policy', {})
        self.min_length = self.config.get('min_length', 32)
        self.allowed_formats = self.config.get('allowed_formats', ['base64', 'hex', 'alphanumeric'])
    
    async def validate(self, credential_data: CredentialData) -> ValidationResult:
        """Validate API key credential"""
        api_key = credential_data.data.get('api_key', '')
        service_name = credential_data.data.get('service_name', '')
        
        issues = []
        recommendations = []
        strength_score = 0.0
        
        # Length check
        if len(api_key) < self.min_length:
            issues.append(f"API key must be at least {self.min_length} characters long")
        else:
            strength_score += 0.3
        
        # Format validation
        format_valid = False
        detected_format = None
        
        if 'base64' in self.allowed_formats and self._is_base64(api_key):
            format_valid = True
            detected_format = 'base64'
            strength_score += 0.2
        elif 'hex' in self.allowed_formats and self._is_hex(api_key):
            format_valid = True
            detected_format = 'hex'
            strength_score += 0.2
        elif 'alphanumeric' in self.allowed_formats and self._is_alphanumeric(api_key):
            format_valid = True
            detected_format = 'alphanumeric'
            strength_score += 0.1
        
        if not format_valid:
            issues.append(f"API key format not recognized. Allowed formats: {', '.join(self.allowed_formats)}")
        
        # Entropy check
        entropy = self._calculate_api_key_entropy(api_key)
        if entropy < 128:  # bits
            issues.append("API key has insufficient entropy")
            recommendations.append("Use a cryptographically secure random generator")
        else:
            strength_score += 0.3
        
        # Service-specific validation
        if service_name:
            service_validation = await self._validate_service_specific(api_key, service_name)
            if not service_validation['valid']:
                issues.extend(service_validation['issues'])
            else:
                strength_score += 0.2
        
        # Expiration check
        expires_at = credential_data.expires_at
        if not expires_at:
            recommendations.append("Consider setting an expiration date for the API key")
        elif expires_at > datetime.utcnow() + timedelta(days=365):
            recommendations.append("Consider shorter expiration periods for better security")
        
        return ValidationResult(
            is_valid=len(issues) == 0,
            strength_score=min(1.0, strength_score),
            issues=issues,
            recommendations=recommendations,
            metadata={
                'format': detected_format,
                'entropy_bits': entropy,
                'length': len(api_key)
            }
        )
    
    def _is_base64(self, s: str) -> bool:
        """Check if string is valid base64"""
        try:
            base64.b64decode(s, validate=True)
            return True
        except Exception:
            return False
    
    def _is_hex(self, s: str) -> bool:
        """Check if string is valid hexadecimal"""
        try:
            int(s, 16)
            return True
        except ValueError:
            return False
    
    def _is_alphanumeric(self, s: str) -> bool:
        """Check if string is alphanumeric"""
        return s.isalnum()
    
    def _calculate_api_key_entropy(self, api_key: str) -> float:
        """Calculate API key entropy in bits"""
        if not api_key:
            return 0.0
        
        # Estimate character space
        charset_size = 0
        if re.search(r'[a-z]', api_key):
            charset_size += 26
        if re.search(r'[A-Z]', api_key):
            charset_size += 26
        if re.search(r'\d', api_key):
            charset_size += 10
        if re.search(r'[+/=]', api_key):  # Base64 characters
            charset_size += 3
        if re.search(r'[-_]', api_key):  # URL-safe base64
            charset_size += 2
        
        import math
        return len(api_key) * math.log2(charset_size) if charset_size > 0 else 0.0
    
    async def _validate_service_specific(self, api_key: str, service_name: str) -> Dict[str, Any]:
        """Validate API key for specific services"""
        service_patterns = {
            'github': r'^gh[ps]_[A-Za-z0-9_]{36,}$',
            'gitlab': r'^glpat-[A-Za-z0-9_-]{20}$',
            'aws': r'^AKIA[A-Z0-9]{16}$',
            'stripe': r'^sk_(test_|live_)[A-Za-z0-9]{24}$',
            'openai': r'^sk-[A-Za-z0-9]{48}$'
        }
        
        pattern = service_patterns.get(service_name.lower())
        if pattern and not re.match(pattern, api_key):
            return {
                'valid': False,
                'issues': [f"API key format doesn't match {service_name} pattern"]
            }
        
        return {'valid': True, 'issues': []}
    
    def get_strength_requirements(self) -> Dict[str, Any]:
        """Get API key strength requirements"""
        return {
            'min_length': self.min_length,
            'allowed_formats': self.allowed_formats,
            'min_entropy_bits': 128
        }


class SSHKeyValidator(CredentialValidator):
    """SSH key credential validator"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get('ssh_key_policy', {})
        self.min_key_size = self.config.get('min_key_size', 2048)
        self.allowed_key_types = self.config.get('allowed_key_types', ['rsa', 'ecdsa', 'ed25519'])
    
    async def validate(self, credential_data: CredentialData) -> ValidationResult:
        """Validate SSH key credential"""
        private_key = credential_data.data.get('private_key', '')
        public_key = credential_data.data.get('public_key', '')
        passphrase = credential_data.data.get('passphrase')
        
        issues = []
        recommendations = []
        strength_score = 0.0
        metadata = {}
        
        try:
            # Parse private key
            if private_key:
                key_obj = serialization.load_pem_private_key(
                    private_key.encode(),
                    password=passphrase.encode() if passphrase else None
                )
                
                # Determine key type and size
                if isinstance(key_obj, rsa.RSAPrivateKey):
                    key_type = 'rsa'
                    key_size = key_obj.key_size
                elif isinstance(key_obj, ec.EllipticCurvePrivateKey):
                    key_type = 'ecdsa'
                    key_size = key_obj.curve.key_size
                elif isinstance(key_obj, ed25519.Ed25519PrivateKey):
                    key_type = 'ed25519'
                    key_size = 256  # Ed25519 is always 256 bits
                else:
                    key_type = 'unknown'
                    key_size = 0
                
                metadata.update({
                    'key_type': key_type,
                    'key_size': key_size,
                    'has_passphrase': bool(passphrase)
                })
                
                # Key type validation
                if key_type not in self.allowed_key_types:
                    issues.append(f"Key type '{key_type}' not allowed. Allowed types: {', '.join(self.allowed_key_types)}")
                else:
                    strength_score += 0.2
                
                # Key size validation
                if key_type == 'rsa' and key_size < self.min_key_size:
                    issues.append(f"RSA key size {key_size} is below minimum {self.min_key_size}")
                elif key_type == 'ecdsa' and key_size < 256:
                    issues.append(f"ECDSA key size {key_size} is too small")
                elif key_size >= self.min_key_size:
                    strength_score += 0.3
                
                # Passphrase check
                if not passphrase:
                    recommendations.append("Consider using a passphrase to protect the private key")
                else:
                    strength_score += 0.2
                    # Validate passphrase strength
                    passphrase_validator = PasswordValidator({'password_policy': {}})
                    passphrase_cred = CredentialData(
                        credential_type=CredentialType.PASSWORD,
                        data={'password': passphrase}
                    )
                    passphrase_result = await passphrase_validator.validate(passphrase_cred)
                    if passphrase_result.strength_score < 0.6:
                        recommendations.append("Use a stronger passphrase for the SSH key")
            
            # Public key validation
            if public_key:
                if not self._validate_public_key_format(public_key):
                    issues.append("Public key format is invalid")
                else:
                    strength_score += 0.1
                
                # Check if public key matches private key
                if private_key and not self._keys_match(private_key, public_key, passphrase):
                    issues.append("Public key does not match private key")
            
            # Key age recommendations
            created_at = credential_data.created_at
            if created_at and (datetime.utcnow() - created_at).days > 365:
                recommendations.append("Consider rotating SSH keys annually")
            
            # Security recommendations
            if key_type == 'rsa' and key_size < 4096:
                recommendations.append("Consider using RSA-4096 or Ed25519 for better security")
            
            if key_type == 'ecdsa':
                recommendations.append("Consider using Ed25519 instead of ECDSA for better security")
        
        except Exception as e:
            issues.append(f"Failed to parse SSH key: {str(e)}")
        
        return ValidationResult(
            is_valid=len(issues) == 0,
            strength_score=min(1.0, strength_score),
            issues=issues,
            recommendations=recommendations,
            metadata=metadata
        )
    
    def _validate_public_key_format(self, public_key: str) -> bool:
        """Validate SSH public key format"""
        try:
            parts = public_key.strip().split()
            if len(parts) < 2:
                return False
            
            key_type = parts[0]
            key_data = parts[1]
            
            # Check key type
            valid_types = ['ssh-rsa', 'ssh-ed25519', 'ecdsa-sha2-nistp256', 'ecdsa-sha2-nistp384', 'ecdsa-sha2-nistp521']
            if key_type not in valid_types:
                return False
            
            # Validate base64 encoding
            base64.b64decode(key_data)
            return True
            
        except Exception:
            return False
    
    def _keys_match(self, private_key: str, public_key: str, passphrase: Optional[str]) -> bool:
        """Check if private and public keys match"""
        try:
            # Load private key
            key_obj = serialization.load_pem_private_key(
                private_key.encode(),
                password=passphrase.encode() if passphrase else None
            )
            
            # Get public key from private key
            derived_public = key_obj.public_key()
            
            # Convert to SSH format for comparison
            if isinstance(derived_public, rsa.RSAPublicKey):
                ssh_public = derived_public.public_bytes(
                    encoding=serialization.Encoding.OpenSSH,
                    format=serialization.PublicFormat.OpenSSH
                ).decode()
            else:
                # For other key types, use OpenSSH format
                ssh_public = derived_public.public_bytes(
                    encoding=serialization.Encoding.OpenSSH,
                    format=serialization.PublicFormat.OpenSSH
                ).decode()
            
            # Compare key data (ignore comment)
            provided_parts = public_key.strip().split()
            derived_parts = ssh_public.strip().split()
            
            return (len(provided_parts) >= 2 and len(derived_parts) >= 2 and
                    provided_parts[0] == derived_parts[0] and
                    provided_parts[1] == derived_parts[1])
            
        except Exception:
            return False
    
    def get_strength_requirements(self) -> Dict[str, Any]:
        """Get SSH key strength requirements"""
        return {
            'min_key_size': self.min_key_size,
            'allowed_key_types': self.allowed_key_types,
            'recommend_passphrase': True
        }


class CertificateValidator(CredentialValidator):
    """X.509 certificate validator"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get('certificate_policy', {})
        self.min_validity_days = self.config.get('min_validity_days', 30)
        self.allowed_key_sizes = self.config.get('allowed_key_sizes', [2048, 4096])
    
    async def validate(self, credential_data: CredentialData) -> ValidationResult:
        """Validate certificate credential"""
        certificate_pem = credential_data.data.get('certificate', '')
        private_key_pem = credential_data.data.get('private_key', '')
        chain_pem = credential_data.data.get('certificate_chain', '')
        
        issues = []
        recommendations = []
        strength_score = 0.0
        metadata = {}
        
        try:
            # Parse certificate
            cert = x509.load_pem_x509_certificate(certificate_pem.encode())
            
            # Basic certificate info
            subject = cert.subject
            issuer = cert.issuer
            not_before = cert.not_valid_before
            not_after = cert.not_valid_after
            
            metadata.update({
                'subject': subject.rfc4514_string(),
                'issuer': issuer.rfc4514_string(),
                'not_before': not_before.isoformat(),
                'not_after': not_after.isoformat(),
                'serial_number': str(cert.serial_number)
            })
            
            # Validity period check
            now = datetime.utcnow()
            if now < not_before:
                issues.append("Certificate is not yet valid")
            elif now > not_after:
                issues.append("Certificate has expired")
            else:
                days_until_expiry = (not_after - now).days
                if days_until_expiry < self.min_validity_days:
                    issues.append(f"Certificate expires in {days_until_expiry} days")
                else:
                    strength_score += 0.2
                
                metadata['days_until_expiry'] = days_until_expiry
            
            # Key algorithm and size check
            public_key = cert.public_key()
            if isinstance(public_key, rsa.RSAPublicKey):
                key_type = 'RSA'
                key_size = public_key.key_size
            elif isinstance(public_key, ec.EllipticCurvePublicKey):
                key_type = 'ECDSA'
                key_size = public_key.curve.key_size
            else:
                key_type = 'Unknown'
                key_size = 0
            
            metadata.update({
                'key_type': key_type,
                'key_size': key_size
            })
            
            if key_size in self.allowed_key_sizes:
                strength_score += 0.2
            else:
                issues.append(f"Key size {key_size} not in allowed sizes: {self.allowed_key_sizes}")
            
            # Signature algorithm check
            signature_algorithm = cert.signature_algorithm_oid._name
            metadata['signature_algorithm'] = signature_algorithm
            
            if 'sha1' in signature_algorithm.lower():
                issues.append("Certificate uses weak SHA-1 signature algorithm")
            else:
                strength_score += 0.1
            
            # Extensions check
            try:
                san_ext = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
                san_names = [name.value for name in san_ext.value]
                metadata['san_names'] = san_names
                strength_score += 0.1
            except x509.ExtensionNotFound:
                recommendations.append("Consider including Subject Alternative Names")
            
            # Key usage check
            try:
                key_usage = cert.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE)
                metadata['key_usage'] = {
                    'digital_signature': key_usage.value.digital_signature,
                    'key_encipherment': key_usage.value.key_encipherment,
                    'key_agreement': key_usage.value.key_agreement
                }
                strength_score += 0.1
            except x509.ExtensionNotFound:
                recommendations.append("Consider specifying key usage extensions")
            
            # Private key validation
            if private_key_pem:
                try:
                    private_key = serialization.load_pem_private_key(
                        private_key_pem.encode(),
                        password=None
                    )
                    
                    # Check if private key matches certificate
                    if self._certificate_key_match(cert, private_key):
                        strength_score += 0.2
                    else:
                        issues.append("Private key does not match certificate")
                        
                except Exception as e:
                    issues.append(f"Failed to load private key: {str(e)}")
            
            # Certificate chain validation
            if chain_pem:
                chain_valid = await self._validate_certificate_chain(certificate_pem, chain_pem)
                if chain_valid:
                    strength_score += 0.1
                else:
                    issues.append("Certificate chain validation failed")
            
            # Self-signed check
            if cert.issuer == cert.subject:
                metadata['self_signed'] = True
                recommendations.append("Self-signed certificates should only be used for testing")
            else:
                metadata['self_signed'] = False
                strength_score += 0.1
        
        except Exception as e:
            issues.append(f"Failed to parse certificate: {str(e)}")
        
        return ValidationResult(
            is_valid=len(issues) == 0,
            strength_score=min(1.0, strength_score),
            issues=issues,
            recommendations=recommendations,
            metadata=metadata
        )
    
    def _certificate_key_match(self, cert: x509.Certificate, private_key) -> bool:
        """Check if certificate and private key match"""
        try:
            cert_public_key = cert.public_key()
            private_public_key = private_key.public_key()
            
            # Compare public key numbers
            if isinstance(cert_public_key, rsa.RSAPublicKey) and isinstance(private_public_key, rsa.RSAPublicKey):
                return (cert_public_key.public_numbers().n == private_public_key.public_numbers().n and
                        cert_public_key.public_numbers().e == private_public_key.public_numbers().e)
            elif isinstance(cert_public_key, ec.EllipticCurvePublicKey) and isinstance(private_public_key, ec.EllipticCurvePublicKey):
                return (cert_public_key.public_numbers().x == private_public_key.public_numbers().x and
                        cert_public_key.public_numbers().y == private_public_key.public_numbers().y)
            
            return False
            
        except Exception:
            return False
    
    async def _validate_certificate_chain(self, cert_pem: str, chain_pem: str) -> bool:
        """Validate certificate chain"""
        try:
            # This is a simplified validation
            # In production, you'd want to use a proper certificate validation library
            cert = x509.load_pem_x509_certificate(cert_pem.encode())
            chain_certs = []
            
            # Parse chain certificates
            for cert_data in chain_pem.split('-----END CERTIFICATE-----'):
                if '-----BEGIN CERTIFICATE-----' in cert_data:
                    cert_data += '-----END CERTIFICATE-----'
                    chain_cert = x509.load_pem_x509_certificate(cert_data.encode())
                    chain_certs.append(chain_cert)
            
            # Basic chain validation (issuer/subject matching)
            current_cert = cert
            for chain_cert in chain_certs:
                if current_cert.issuer == chain_cert.subject:
                    current_cert = chain_cert
                else:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def get_strength_requirements(self) -> Dict[str, Any]:
        """Get certificate strength requirements"""
        return {
            'min_validity_days': self.min_validity_days,
            'allowed_key_sizes': self.allowed_key_sizes,
            'require_san': False,
            'require_key_usage': False
        }


class CredentialTypeManager:
    """Manager for all credential types and validators"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize validators
        self.validators = {
            CredentialType.PASSWORD: PasswordValidator(config),
            CredentialType.API_KEY: APIKeyValidator(config),
            CredentialType.SSH_KEY: SSHKeyValidator(config),
            CredentialType.CERTIFICATE: CertificateValidator(config)
        }
    
    async def validate_credential(self, credential_data: CredentialData) -> ValidationResult:
        """Validate credential based on its type"""
        try:
            validator = self.validators.get(credential_data.credential_type)
            if not validator:
                return ValidationResult(
                    is_valid=True,  # Unknown types are considered valid
                    strength_score=0.5,
                    issues=[],
                    recommendations=[f"No validator available for {credential_data.credential_type.value}"],
                    metadata={'validator': 'none'}
                )
            
            result = await validator.validate(credential_data)
            result.metadata['validator'] = credential_data.credential_type.value
            
            return result
            
        except Exception as e:
            self.logger.error(f"Credential validation failed: {str(e)}")
            return ValidationResult(
                is_valid=False,
                strength_score=0.0,
                issues=[f"Validation error: {str(e)}"],
                recommendations=[],
                metadata={'error': str(e)}
            )
    
    def get_supported_types(self) -> List[CredentialType]:
        """Get list of supported credential types"""
        return list(CredentialType)
    
    def get_type_requirements(self, credential_type: CredentialType) -> Dict[str, Any]:
        """Get requirements for a specific credential type"""
        validator = self.validators.get(credential_type)
        if validator:
            return validator.get_strength_requirements()
        return {}
    
    async def generate_credential(self, credential_type: CredentialType, 
                                parameters: Dict[str, Any] = None) -> CredentialData:
        """Generate a new credential of the specified type"""
        params = parameters or {}
        
        if credential_type == CredentialType.PASSWORD:
            return await self._generate_password(params)
        elif credential_type == CredentialType.API_KEY:
            return await self._generate_api_key(params)
        elif credential_type == CredentialType.SSH_KEY:
            return await self._generate_ssh_key(params)
        elif credential_type == CredentialType.WEBHOOK_SECRET:
            return await self._generate_webhook_secret(params)
        else:
            raise ValueError(f"Generation not supported for {credential_type.value}")
    
    async def _generate_password(self, params: Dict[str, Any]) -> CredentialData:
        """Generate a secure password"""
        length = params.get('length', 16)
        include_symbols = params.get('include_symbols', True)
        
        # Character sets
        lowercase = 'abcdefghijklmnopqrstuvwxyz'
        uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        digits = '0123456789'
        symbols = '!@#$%^&*()_+-=[]{}|;:,.<>?'
        
        # Build character set
        charset = lowercase + uppercase + digits
        if include_symbols:
            charset += symbols
        
        # Generate password ensuring at least one character from each required set
        password = []
        password.append(secrets.choice(lowercase))
        password.append(secrets.choice(uppercase))
        password.append(secrets.choice(digits))
        if include_symbols:
            password.append(secrets.choice(symbols))
        
        # Fill remaining length
        for _ in range(length - len(password)):
            password.append(secrets.choice(charset))
        
        # Shuffle the password
        secrets.SystemRandom().shuffle(password)
        
        return CredentialData(
            credential_type=CredentialType.PASSWORD,
            data={'password': ''.join(password)},
            metadata={'generated': True, 'length': length}
        )
    
    async def _generate_api_key(self, params: Dict[str, Any]) -> CredentialData:
        """Generate a secure API key"""
        length = params.get('length', 32)
        format_type = params.get('format', 'base64')
        
        if format_type == 'base64':
            # Generate random bytes and encode as base64
            random_bytes = secrets.token_bytes(length)
            api_key = base64.b64encode(random_bytes).decode('ascii')
        elif format_type == 'hex':
            api_key = secrets.token_hex(length)
        else:  # alphanumeric
            api_key = secrets.token_urlsafe(length)
        
        return CredentialData(
            credential_type=CredentialType.API_KEY,
            data={'api_key': api_key},
            metadata={'generated': True, 'format': format_type, 'length': len(api_key)}
        )
    
    async def _generate_ssh_key(self, params: Dict[str, Any]) -> CredentialData:
        """Generate SSH key pair"""
        key_type = params.get('key_type', 'ed25519')
        key_size = params.get('key_size', 2048)
        passphrase = params.get('passphrase')
        
        if key_type == 'rsa':
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_size
            )
        elif key_type == 'ed25519':
            private_key = ed25519.Ed25519PrivateKey.generate()
        else:
            raise ValueError(f"Unsupported SSH key type: {key_type}")
        
        # Serialize private key
        encryption_algorithm = serialization.BestAvailableEncryption(passphrase.encode()) if passphrase else serialization.NoEncryption()
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.OpenSSH,
            encryption_algorithm=encryption_algorithm
        ).decode()
        
        # Generate public key
        public_key = private_key.public_key()
        public_ssh = public_key.public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH
        ).decode()
        
        return CredentialData(
            credential_type=CredentialType.SSH_KEY,
            data={
                'private_key': private_pem,
                'public_key': public_ssh,
                'passphrase': passphrase
            },
            metadata={'generated': True, 'key_type': key_type, 'key_size': key_size}
        )
    
    async def _generate_webhook_secret(self, params: Dict[str, Any]) -> CredentialData:
        """Generate webhook secret"""
        length = params.get('length', 32)
        secret = secrets.token_urlsafe(length)
        
        return CredentialData(
            credential_type=CredentialType.WEBHOOK_SECRET,
            data={'secret': secret},
            metadata={'generated': True, 'length': length}
        )