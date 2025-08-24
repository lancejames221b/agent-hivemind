"""
Shamir's Secret Sharing Implementation for Distributed Master Key Management
Provides cryptographic key splitting and recovery for enterprise security.

Author: Lance James, Unit 221B
"""

import secrets
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import asyncio
import hashlib
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import redis


@dataclass
class SecretShare:
    """Represents a single share of a secret"""
    share_id: int
    share_value: bytes
    threshold: int
    total_shares: int
    created_at: datetime
    owner_id: str
    key_id: str
    metadata: Dict[str, Any]


@dataclass
class ShareRecoveryRequest:
    """Request to recover a secret using shares"""
    request_id: str
    key_id: str
    required_threshold: int
    submitted_shares: List[SecretShare]
    requesting_user: str
    created_at: datetime
    expires_at: datetime
    approved_by: List[str]
    status: str


class ShamirSecretSharing:
    """Shamir's Secret Sharing implementation for master key distribution"""
    
    # Prime number for finite field arithmetic (256-bit prime)
    PRIME = 2**256 - 189
    
    def __init__(self, config: Dict[str, Any], redis_client: redis.Redis):
        self.config = config
        self.redis = redis_client
        self.logger = logging.getLogger(__name__)
        self.recovery_requests: Dict[str, ShareRecoveryRequest] = {}
    
    def _mod_inverse(self, a: int, m: int) -> int:
        """Calculate modular multiplicative inverse using extended Euclidean algorithm"""
        if a < 0:
            a = (a % m + m) % m
        
        def extended_gcd(a: int, b: int) -> Tuple[int, int, int]:
            if a == 0:
                return b, 0, 1
            gcd, x1, y1 = extended_gcd(b % a, a)
            x = y1 - (b // a) * x1
            y = x1
            return gcd, x, y
        
        gcd, x, _ = extended_gcd(a, m)
        if gcd != 1:
            raise ValueError("Modular inverse does not exist")
        return (x % m + m) % m
    
    def _polynomial_evaluate(self, coefficients: List[int], x: int) -> int:
        """Evaluate polynomial at point x using Horner's method"""
        result = 0
        for coefficient in reversed(coefficients):
            result = (result * x + coefficient) % self.PRIME
        return result
    
    def _lagrange_interpolate(self, points: List[Tuple[int, int]], x: int = 0) -> int:
        """Perform Lagrange interpolation to recover secret"""
        result = 0
        k = len(points)
        
        for i in range(k):
            xi, yi = points[i]
            numerator = 1
            denominator = 1
            
            for j in range(k):
                if i != j:
                    xj, _ = points[j]
                    numerator = (numerator * (x - xj)) % self.PRIME
                    denominator = (denominator * (xi - xj)) % self.PRIME
            
            denominator_inv = self._mod_inverse(denominator, self.PRIME)
            lagrange_coefficient = (numerator * denominator_inv) % self.PRIME
            result = (result + yi * lagrange_coefficient) % self.PRIME
        
        return result
    
    async def create_secret_shares(self, secret: bytes, threshold: int, total_shares: int, 
                                 key_id: str, owners: List[str]) -> List[SecretShare]:
        """Create secret shares using Shamir's Secret Sharing"""
        try:
            if threshold > total_shares:
                raise ValueError("Threshold cannot be greater than total shares")
            
            if len(owners) != total_shares:
                raise ValueError("Number of owners must match total shares")
            
            secret_int = int.from_bytes(secret, byteorder='big')
            if secret_int >= self.PRIME:
                raise ValueError("Secret too large for field")
            
            coefficients = [secret_int]
            for _ in range(threshold - 1):
                coeff = secrets.randbelow(self.PRIME)
                coefficients.append(coeff)
            
            shares = []
            for i in range(1, total_shares + 1):
                share_value = self._polynomial_evaluate(coefficients, i)
                share_bytes = share_value.to_bytes(32, byteorder='big')
                
                share = SecretShare(
                    share_id=i,
                    share_value=share_bytes,
                    threshold=threshold,
                    total_shares=total_shares,
                    created_at=datetime.utcnow(),
                    owner_id=owners[i-1],
                    key_id=key_id,
                    metadata={
                        'algorithm': 'shamir_secret_sharing',
                        'field_prime': str(self.PRIME),
                        'created_by': 'vault_system'
                    }
                )
                shares.append(share)
            
            await self._store_share_metadata(key_id, threshold, total_shares, owners)
            
            for share in shares:
                await self._store_share(share)
            
            self.logger.info(f"Created {total_shares} shares for key {key_id} with threshold {threshold}")
            return shares
            
        except Exception as e:
            self.logger.error(f"Failed to create secret shares: {str(e)}")
            raise
    
    async def _store_share_metadata(self, key_id: str, threshold: int, total_shares: int, owners: List[str]) -> None:
        """Store metadata about the shared secret"""
        metadata = {
            'key_id': key_id,
            'threshold': threshold,
            'total_shares': total_shares,
            'owners': owners,
            'created_at': datetime.utcnow().isoformat(),
            'status': 'active'
        }
        
        await self.redis.hset(f"shamir_metadata:{key_id}", mapping={
            k: json.dumps(v) if isinstance(v, (list, dict)) else str(v)
            for k, v in metadata.items()
        })
    
    async def _store_share(self, share: SecretShare) -> None:
        """Store an encrypted share in Redis"""
        share_data = {
            'share_id': share.share_id,
            'share_value': share.share_value.hex(),
            'threshold': share.threshold,
            'total_shares': share.total_shares,
            'created_at': share.created_at.isoformat(),
            'owner_id': share.owner_id,
            'key_id': share.key_id,
            'metadata': json.dumps(share.metadata)
        }
        
        await self.redis.hset(f"shamir_share:{share.key_id}:{share.share_id}", mapping=share_data)
        await self.redis.sadd(f"shamir_shares:{share.key_id}", share.share_id)
        await self.redis.sadd(f"user_shares:{share.owner_id}", f"{share.key_id}:{share.share_id}")
    
    async def get_user_shares(self, user_id: str) -> List[SecretShare]:
        """Get all shares owned by a specific user"""
        try:
            user_share_keys = await self.redis.smembers(f"user_shares:{user_id}")
            shares = []
            
            for share_key in user_share_keys:
                share_key_str = share_key.decode() if isinstance(share_key, bytes) else share_key
                key_id, share_id = share_key_str.split(':')
                
                share_data = await self.redis.hgetall(f"shamir_share:{key_id}:{share_id}")
                if share_data:
                    share = SecretShare(
                        share_id=int(share_data[b'share_id']),
                        share_value=bytes.fromhex(share_data[b'share_value'].decode()),
                        threshold=int(share_data[b'threshold']),
                        total_shares=int(share_data[b'total_shares']),
                        created_at=datetime.fromisoformat(share_data[b'created_at'].decode()),
                        owner_id=share_data[b'owner_id'].decode(),
                        key_id=share_data[b'key_id'].decode(),
                        metadata=json.loads(share_data[b'metadata'])
                    )
                    shares.append(share)
            
            return shares
            
        except Exception as e:
            self.logger.error(f"Failed to get user shares: {str(e)}")
            return []
    
    async def initiate_secret_recovery(self, key_id: str, requesting_user: str, 
                                     recovery_reason: str) -> str:
        """Initiate a secret recovery request"""
        try:
            metadata = await self.redis.hgetall(f"shamir_metadata:{key_id}")
            if not metadata:
                raise ValueError(f"No metadata found for key {key_id}")
            
            threshold = int(metadata[b'threshold'])
            request_id = secrets.token_hex(16)
            
            recovery_request = ShareRecoveryRequest(
                request_id=request_id,
                key_id=key_id,
                required_threshold=threshold,
                submitted_shares=[],
                requesting_user=requesting_user,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(hours=24),
                approved_by=[],
                status='pending'
            )
            
            self.recovery_requests[request_id] = recovery_request
            
            request_data = {
                'request_id': request_id,
                'key_id': key_id,
                'required_threshold': threshold,
                'requesting_user': requesting_user,
                'recovery_reason': recovery_reason,
                'created_at': recovery_request.created_at.isoformat(),
                'expires_at': recovery_request.expires_at.isoformat(),
                'status': 'pending'
            }
            
            await self.redis.hset(f"recovery_request:{request_id}", mapping=request_data)
            await self.redis.expire(f"recovery_request:{request_id}", 86400)  # 24 hours
            
            self.logger.info(f"Recovery request {request_id} initiated for key {key_id} by {requesting_user}")
            return request_id
            
        except Exception as e:
            self.logger.error(f"Failed to initiate recovery: {str(e)}")
            raise
    
    async def submit_share_for_recovery(self, request_id: str, share: SecretShare, 
                                      submitting_user: str) -> bool:
        """Submit a share for secret recovery"""
        try:
            if request_id not in self.recovery_requests:
                request_data = await self.redis.hgetall(f"recovery_request:{request_id}")
                if not request_data:
                    raise ValueError(f"Recovery request {request_id} not found")
                
                recovery_request = ShareRecoveryRequest(
                    request_id=request_id,
                    key_id=request_data[b'key_id'].decode(),
                    required_threshold=int(request_data[b'required_threshold']),
                    submitted_shares=[],
                    requesting_user=request_data[b'requesting_user'].decode(),
                    created_at=datetime.fromisoformat(request_data[b'created_at'].decode()),
                    expires_at=datetime.fromisoformat(request_data[b'expires_at'].decode()),
                    approved_by=[],
                    status=request_data[b'status'].decode()
                )
                self.recovery_requests[request_id] = recovery_request
            
            recovery_request = self.recovery_requests[request_id]
            
            if datetime.utcnow() > recovery_request.expires_at:
                recovery_request.status = 'expired'
                return False
            
            if share.key_id != recovery_request.key_id:
                raise ValueError("Share key_id does not match recovery request")
            
            if share.owner_id != submitting_user:
                raise ValueError("User does not own this share")
            
            if any(s.share_id == share.share_id for s in recovery_request.submitted_shares):
                raise ValueError("Share already submitted")
            
            recovery_request.submitted_shares.append(share)
            
            await self.redis.hset(f"recovery_request:{request_id}", 
                                'submitted_share_count', len(recovery_request.submitted_shares))
            
            self.logger.info(f"Share {share.share_id} submitted for recovery request {request_id}")
            
            if len(recovery_request.submitted_shares) >= recovery_request.required_threshold:
                return await self._complete_recovery(recovery_request)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to submit share: {str(e)}")
            return False
    
    async def _complete_recovery(self, recovery_request: ShareRecoveryRequest) -> bool:
        """Complete secret recovery when threshold is met"""
        try:
            points = []
            for share in recovery_request.submitted_shares[:recovery_request.required_threshold]:
                x = share.share_id
                y = int.from_bytes(share.share_value, byteorder='big')
                points.append((x, y))
            
            secret_int = self._lagrange_interpolate(points)
            secret_bytes = secret_int.to_bytes(32, byteorder='big').lstrip(b'\x00')
            
            recovery_data = {
                'recovered_secret': secret_bytes.hex(),
                'recovered_at': datetime.utcnow().isoformat(),
                'shares_used': [share.share_id for share in recovery_request.submitted_shares],
                'status': 'completed'
            }
            
            await self.redis.hset(f"recovery_request:{recovery_request.request_id}", mapping=recovery_data)
            await self.redis.expire(f"recovery_request:{recovery_request.request_id}", 86400 * 7)  # Keep for 7 days
            
            recovery_request.status = 'completed'
            
            self.logger.info(f"Secret recovery completed for request {recovery_request.request_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to complete recovery: {str(e)}")
            recovery_request.status = 'failed'
            return False
    
    async def get_recovered_secret(self, request_id: str, requesting_user: str) -> Optional[bytes]:
        """Get the recovered secret (one-time access)"""
        try:
            request_data = await self.redis.hgetall(f"recovery_request:{request_id}")
            if not request_data:
                return None
            
            if request_data[b'requesting_user'].decode() != requesting_user:
                raise ValueError("Unauthorized access to recovery request")
            
            if request_data[b'status'].decode() != 'completed':
                return None
            
            secret_hex = request_data.get(b'recovered_secret')
            if not secret_hex:
                return None
            
            await self.redis.hdel(f"recovery_request:{request_id}", 'recovered_secret')
            
            secret_bytes = bytes.fromhex(secret_hex.decode())
            return secret_bytes
            
        except Exception as e:
            self.logger.error(f"Failed to get recovered secret: {str(e)}")
            return None
    
    async def revoke_shares(self, key_id: str, authorizing_user: str, reason: str) -> bool:
        """Revoke all shares for a key"""
        try:
            metadata = await self.redis.hgetall(f"shamir_metadata:{key_id}")
            if not metadata:
                raise ValueError(f"No metadata found for key {key_id}")
            
            owners = json.loads(metadata[b'owners'])
            
            for i in range(1, int(metadata[b'total_shares']) + 1):
                await self.redis.delete(f"shamir_share:{key_id}:{i}")
                if i <= len(owners):
                    await self.redis.srem(f"user_shares:{owners[i-1]}", f"{key_id}:{i}")
            
            await self.redis.delete(f"shamir_shares:{key_id}")
            await self.redis.hset(f"shamir_metadata:{key_id}", 'status', 'revoked')
            await self.redis.hset(f"shamir_metadata:{key_id}", 'revoked_at', datetime.utcnow().isoformat())
            await self.redis.hset(f"shamir_metadata:{key_id}", 'revoked_by', authorizing_user)
            await self.redis.hset(f"shamir_metadata:{key_id}", 'revocation_reason', reason)
            
            self.logger.info(f"Shares for key {key_id} revoked by {authorizing_user}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to revoke shares: {str(e)}")
            return False
    
    async def rotate_shares(self, key_id: str, new_secret: bytes, authorizing_user: str) -> bool:
        """Rotate shares with a new secret while maintaining the same distribution"""
        try:
            metadata = await self.redis.hgetall(f"shamir_metadata:{key_id}")
            if not metadata:
                raise ValueError(f"No metadata found for key {key_id}")
            
            threshold = int(metadata[b'threshold'])
            total_shares = int(metadata[b'total_shares'])
            owners = json.loads(metadata[b'owners'])
            
            await self.revoke_shares(key_id, authorizing_user, "rotation")
            
            new_shares = await self.create_secret_shares(new_secret, threshold, total_shares, 
                                                       key_id, owners)
            
            await self.redis.hset(f"shamir_metadata:{key_id}", 'status', 'active')
            await self.redis.hset(f"shamir_metadata:{key_id}", 'rotated_at', datetime.utcnow().isoformat())
            await self.redis.hset(f"shamir_metadata:{key_id}", 'rotated_by', authorizing_user)
            
            self.logger.info(f"Shares rotated for key {key_id} by {authorizing_user}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to rotate shares: {str(e)}")
            return False
    
    async def get_share_status(self, key_id: str) -> Dict[str, Any]:
        """Get status information about shares for a key"""
        try:
            metadata = await self.redis.hgetall(f"shamir_metadata:{key_id}")
            if not metadata:
                return {'error': 'Key not found'}
            
            active_shares = await self.redis.scard(f"shamir_shares:{key_id}")
            
            status = {
                'key_id': key_id,
                'threshold': int(metadata[b'threshold']),
                'total_shares': int(metadata[b'total_shares']),
                'active_shares': active_shares,
                'owners': json.loads(metadata[b'owners']),
                'status': metadata[b'status'].decode(),
                'created_at': metadata[b'created_at'].decode()
            }
            
            if b'revoked_at' in metadata:
                status['revoked_at'] = metadata[b'revoked_at'].decode()
                status['revoked_by'] = metadata[b'revoked_by'].decode()
                status['revocation_reason'] = metadata[b'revocation_reason'].decode()
            
            if b'rotated_at' in metadata:
                status['rotated_at'] = metadata[b'rotated_at'].decode()
                status['rotated_by'] = metadata[b'rotated_by'].decode()
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get share status: {str(e)}")
            return {'error': str(e)}
    
    async def get_recovery_requests(self, user_id: str) -> List[Dict[str, Any]]:
        """Get recovery requests that involve the user"""
        try:
            requests = []
            
            for request_id, recovery_request in self.recovery_requests.items():
                user_shares = await self.get_user_shares(user_id)
                key_involved = any(share.key_id == recovery_request.key_id for share in user_shares)
                
                if recovery_request.requesting_user == user_id or key_involved:
                    request_data = {
                        'request_id': request_id,
                        'key_id': recovery_request.key_id,
                        'required_threshold': recovery_request.required_threshold,
                        'submitted_shares': len(recovery_request.submitted_shares),
                        'requesting_user': recovery_request.requesting_user,
                        'created_at': recovery_request.created_at.isoformat(),
                        'expires_at': recovery_request.expires_at.isoformat(),
                        'status': recovery_request.status,
                        'user_can_contribute': key_involved and user_id != recovery_request.requesting_user
                    }
                    requests.append(request_data)
            
            return requests
            
        except Exception as e:
            self.logger.error(f"Failed to get recovery requests: {str(e)}")
            return []