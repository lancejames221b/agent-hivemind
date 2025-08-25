"""
Performance Optimization Layer for Credential Vault
Implements caching, batch operations, and async processing optimizations.

Author: Lance James, Unit 221B
"""

import asyncio
import logging
import json
import time
import hashlib
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import weakref
from concurrent.futures import ThreadPoolExecutor, as_completed
import redis
import asyncpg
from contextlib import asynccontextmanager

from .encryption_engine import EncryptionEngine, EncryptedData
from .credential_types import CredentialData, CredentialType
from .database_manager import DatabaseManager


class CacheStrategy(Enum):
    """Cache strategies"""
    LRU = "lru"
    LFU = "lfu"
    TTL = "ttl"
    WRITE_THROUGH = "write_through"
    WRITE_BACK = "write_back"


class BatchOperationType(Enum):
    """Types of batch operations"""
    ENCRYPT = "encrypt"
    DECRYPT = "decrypt"
    STORE = "store"
    RETRIEVE = "retrieve"
    VALIDATE = "validate"
    DELETE = "delete"


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl: Optional[int] = None
    size: int = 0
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if not self.ttl:
            return False
        return (datetime.utcnow() - self.created_at).total_seconds() > self.ttl


@dataclass
class BatchOperation:
    """Batch operation definition"""
    operation_id: str
    operation_type: BatchOperationType
    items: List[Any]
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    callback: Optional[Callable] = None


@dataclass
class PerformanceMetrics:
    """Performance metrics tracking"""
    cache_hits: int = 0
    cache_misses: int = 0
    batch_operations: int = 0
    avg_response_time: float = 0.0
    total_operations: int = 0
    memory_usage: int = 0
    concurrent_operations: int = 0


class MemoryCache:
    """High-performance in-memory cache with multiple strategies"""
    
    def __init__(self, max_size: int = 1000, strategy: CacheStrategy = CacheStrategy.LRU,
                 default_ttl: Optional[int] = None):
        self.max_size = max_size
        self.strategy = strategy
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.access_order = deque()  # For LRU
        self.access_frequency = defaultdict(int)  # For LFU
        self.size_bytes = 0
        self.lock = asyncio.Lock()
        
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        async with self.lock:
            entry = self.cache.get(key)
            if not entry:
                return None
            
            # Check expiration
            if entry.is_expired:
                await self._remove_entry(key)
                return None
            
            # Update access statistics
            entry.last_accessed = datetime.utcnow()
            entry.access_count += 1
            
            # Update strategy-specific data
            if self.strategy == CacheStrategy.LRU:
                self.access_order.remove(key)
                self.access_order.append(key)
            elif self.strategy == CacheStrategy.LFU:
                self.access_frequency[key] += 1
            
            return entry.value
    
    async def put(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Put value in cache"""
        async with self.lock:
            # Calculate size
            value_size = self._calculate_size(value)
            
            # Check if we need to evict
            if key not in self.cache and len(self.cache) >= self.max_size:
                await self._evict()
            
            # Remove existing entry if present
            if key in self.cache:
                await self._remove_entry(key)
            
            # Create new entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.utcnow(),
                last_accessed=datetime.utcnow(),
                ttl=ttl or self.default_ttl,
                size=value_size
            )
            
            self.cache[key] = entry
            self.size_bytes += value_size
            
            # Update strategy-specific data
            if self.strategy == CacheStrategy.LRU:
                self.access_order.append(key)
            elif self.strategy == CacheStrategy.LFU:
                self.access_frequency[key] = 1
            
            return True
    
    async def remove(self, key: str) -> bool:
        """Remove entry from cache"""
        async with self.lock:
            return await self._remove_entry(key)
    
    async def _remove_entry(self, key: str) -> bool:
        """Remove entry (internal method)"""
        entry = self.cache.get(key)
        if not entry:
            return False
        
        del self.cache[key]
        self.size_bytes -= entry.size
        
        # Update strategy-specific data
        if self.strategy == CacheStrategy.LRU and key in self.access_order:
            self.access_order.remove(key)
        elif self.strategy == CacheStrategy.LFU and key in self.access_frequency:
            del self.access_frequency[key]
        
        return True
    
    async def _evict(self) -> None:
        """Evict entries based on strategy"""
        if not self.cache:
            return
        
        if self.strategy == CacheStrategy.LRU:
            # Remove least recently used
            if self.access_order:
                oldest_key = self.access_order[0]
                await self._remove_entry(oldest_key)
        
        elif self.strategy == CacheStrategy.LFU:
            # Remove least frequently used
            if self.access_frequency:
                lfu_key = min(self.access_frequency.keys(), 
                            key=lambda k: self.access_frequency[k])
                await self._remove_entry(lfu_key)
        
        elif self.strategy == CacheStrategy.TTL:
            # Remove expired entries first
            expired_keys = [
                key for key, entry in self.cache.items() 
                if entry.is_expired
            ]
            if expired_keys:
                for key in expired_keys:
                    await self._remove_entry(key)
            else:
                # If no expired entries, remove oldest
                oldest_key = min(self.cache.keys(), 
                               key=lambda k: self.cache[k].created_at)
                await self._remove_entry(oldest_key)
    
    def _calculate_size(self, value: Any) -> int:
        """Estimate memory size of value"""
        try:
            if isinstance(value, (str, bytes)):
                return len(value)
            elif isinstance(value, dict):
                return len(json.dumps(value))
            else:
                return len(str(value))
        except:
            return 100  # Default size estimate
    
    async def clear(self) -> None:
        """Clear all cache entries"""
        async with self.lock:
            self.cache.clear()
            self.access_order.clear()
            self.access_frequency.clear()
            self.size_bytes = 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        async with self.lock:
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'size_bytes': self.size_bytes,
                'strategy': self.strategy.value,
                'hit_ratio': 0.0,  # Would need to track hits/misses
                'expired_entries': sum(1 for entry in self.cache.values() if entry.is_expired)
            }


class BatchProcessor:
    """Batch operation processor for improved performance"""
    
    def __init__(self, max_batch_size: int = 100, batch_timeout: float = 5.0,
                 max_workers: int = 4):
        self.max_batch_size = max_batch_size
        self.batch_timeout = batch_timeout
        self.max_workers = max_workers
        self.pending_batches: Dict[BatchOperationType, List[BatchOperation]] = defaultdict(list)
        self.batch_queue = asyncio.Queue()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.processing = False
        self.logger = logging.getLogger(__name__)
        
    async def start(self):
        """Start batch processor"""
        if not self.processing:
            self.processing = True
            asyncio.create_task(self._process_batches())
            self.logger.info("Batch processor started")
    
    async def stop(self):
        """Stop batch processor"""
        self.processing = False
        self.executor.shutdown(wait=True)
        self.logger.info("Batch processor stopped")
    
    async def submit_batch(self, operation: BatchOperation) -> str:
        """Submit batch operation"""
        await self.batch_queue.put(operation)
        return operation.operation_id
    
    async def _process_batches(self):
        """Process batch operations"""
        while self.processing:
            try:
                # Collect operations for batching
                batch_operations = []
                timeout_start = time.time()
                
                while (len(batch_operations) < self.max_batch_size and 
                       time.time() - timeout_start < self.batch_timeout):
                    try:
                        operation = await asyncio.wait_for(
                            self.batch_queue.get(), 
                            timeout=0.1
                        )
                        batch_operations.append(operation)
                    except asyncio.TimeoutError:
                        break
                
                if batch_operations:
                    await self._execute_batch(batch_operations)
                
                await asyncio.sleep(0.01)  # Small delay to prevent busy waiting
                
            except Exception as e:
                self.logger.error(f"Batch processing error: {str(e)}")
                await asyncio.sleep(1)
    
    async def _execute_batch(self, operations: List[BatchOperation]):
        """Execute batch of operations"""
        try:
            # Group operations by type
            grouped_ops = defaultdict(list)
            for op in operations:
                grouped_ops[op.operation_type].append(op)
            
            # Execute each group
            for op_type, ops in grouped_ops.items():
                if op_type == BatchOperationType.ENCRYPT:
                    await self._batch_encrypt(ops)
                elif op_type == BatchOperationType.DECRYPT:
                    await self._batch_decrypt(ops)
                elif op_type == BatchOperationType.STORE:
                    await self._batch_store(ops)
                elif op_type == BatchOperationType.RETRIEVE:
                    await self._batch_retrieve(ops)
                
        except Exception as e:
            self.logger.error(f"Batch execution error: {str(e)}")
    
    async def _batch_encrypt(self, operations: List[BatchOperation]):
        """Batch encrypt operations"""
        # Implementation would depend on encryption engine
        pass
    
    async def _batch_decrypt(self, operations: List[BatchOperation]):
        """Batch decrypt operations"""
        # Implementation would depend on encryption engine
        pass
    
    async def _batch_store(self, operations: List[BatchOperation]):
        """Batch store operations"""
        # Implementation would depend on database manager
        pass
    
    async def _batch_retrieve(self, operations: List[BatchOperation]):
        """Batch retrieve operations"""
        # Implementation would depend on database manager
        pass


class PerformanceOptimizer:
    """Main performance optimization coordinator"""
    
    def __init__(self, config: Dict[str, Any], redis_client: Optional[redis.Redis],
                 encryption_engine: EncryptionEngine, database_manager: DatabaseManager):
        self.config = config
        self.redis = redis_client
        self.encryption_engine = encryption_engine
        self.database_manager = database_manager
        self.logger = logging.getLogger(__name__)
        
        # Performance configuration
        perf_config = config.get('vault', {}).get('performance', {})
        
        # Initialize caches
        cache_config = perf_config.get('cache', {})
        self.metadata_cache = MemoryCache(
            max_size=cache_config.get('metadata_max_size', 1000),
            strategy=CacheStrategy(cache_config.get('metadata_strategy', 'lru')),
            default_ttl=cache_config.get('metadata_ttl', 300)
        )
        
        self.credential_cache = MemoryCache(
            max_size=cache_config.get('credential_max_size', 500),
            strategy=CacheStrategy(cache_config.get('credential_strategy', 'ttl')),
            default_ttl=cache_config.get('credential_ttl', 60)  # Shorter TTL for sensitive data
        )
        
        # Initialize batch processor
        batch_config = perf_config.get('batch', {})
        self.batch_processor = BatchProcessor(
            max_batch_size=batch_config.get('max_size', 100),
            batch_timeout=batch_config.get('timeout', 5.0),
            max_workers=batch_config.get('max_workers', 4)
        )
        
        # Performance metrics
        self.metrics = PerformanceMetrics()
        self.operation_times = deque(maxlen=1000)  # Keep last 1000 operation times
        
        # Connection pooling
        self.connection_pool_size = perf_config.get('connection_pool_size', 10)
        
    async def initialize(self) -> bool:
        """Initialize performance optimizer"""
        try:
            await self.batch_processor.start()
            
            # Start background tasks
            asyncio.create_task(self._cache_cleanup_task())
            asyncio.create_task(self._metrics_update_task())
            
            self.logger.info("Performance optimizer initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize performance optimizer: {str(e)}")
            return False
    
    async def shutdown(self):
        """Shutdown performance optimizer"""
        await self.batch_processor.stop()
        await self.metadata_cache.clear()
        await self.credential_cache.clear()
        self.logger.info("Performance optimizer shutdown")
    
    async def get_cached_metadata(self, credential_id: str) -> Optional[Dict[str, Any]]:
        """Get cached credential metadata"""
        start_time = time.time()
        
        try:
            # Check memory cache first
            cache_key = f"metadata:{credential_id}"
            cached_data = await self.metadata_cache.get(cache_key)
            
            if cached_data:
                self.metrics.cache_hits += 1
                return cached_data
            
            # Check Redis cache
            if self.redis:
                redis_key = f"vault:metadata:{credential_id}"
                redis_data = self.redis.get(redis_key)
                if redis_data:
                    data = json.loads(redis_data)
                    # Store in memory cache for faster access
                    await self.metadata_cache.put(cache_key, data)
                    self.metrics.cache_hits += 1
                    return data
            
            self.metrics.cache_misses += 1
            return None
            
        finally:
            self._record_operation_time(time.time() - start_time)
    
    async def cache_metadata(self, credential_id: str, metadata: Dict[str, Any],
                           ttl: Optional[int] = None) -> bool:
        """Cache credential metadata"""
        try:
            cache_key = f"metadata:{credential_id}"
            
            # Store in memory cache
            await self.metadata_cache.put(cache_key, metadata, ttl)
            
            # Store in Redis cache
            if self.redis:
                redis_key = f"vault:metadata:{credential_id}"
                redis_ttl = ttl or 300
                self.redis.setex(redis_key, redis_ttl, json.dumps(metadata))
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cache metadata: {str(e)}")
            return False
    
    async def get_cached_credential(self, credential_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached decrypted credential (with security considerations)"""
        # Note: Caching decrypted credentials is risky and should be done carefully
        # This implementation uses very short TTL and includes user context
        
        cache_key = f"credential:{credential_id}:{hashlib.sha256(user_id.encode()).hexdigest()[:16]}"
        return await self.credential_cache.get(cache_key)
    
    async def cache_credential(self, credential_id: str, user_id: str, 
                             credential_data: Dict[str, Any], ttl: int = 60) -> bool:
        """Cache decrypted credential with security measures"""
        try:
            cache_key = f"credential:{credential_id}:{hashlib.sha256(user_id.encode()).hexdigest()[:16]}"
            
            # Only cache in memory with very short TTL
            await self.credential_cache.put(cache_key, credential_data, ttl)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cache credential: {str(e)}")
            return False
    
    async def batch_encrypt_credentials(self, credentials: List[Tuple[Dict[str, Any], str]]) -> List[EncryptedData]:
        """Batch encrypt multiple credentials"""
        start_time = time.time()
        
        try:
            # Use encryption engine's batch encrypt
            data_list = [(json.dumps(cred_data).encode(), password) for cred_data, password in credentials]
            results = await self.encryption_engine.batch_encrypt(data_list)
            
            self.metrics.batch_operations += 1
            return results
            
        finally:
            self._record_operation_time(time.time() - start_time)
    
    async def batch_decrypt_credentials(self, encrypted_credentials: List[Tuple[EncryptedData, str]]) -> List[Dict[str, Any]]:
        """Batch decrypt multiple credentials"""
        start_time = time.time()
        
        try:
            # Use encryption engine's batch decrypt
            decrypted_data = await self.encryption_engine.batch_decrypt(encrypted_credentials)
            
            # Parse JSON data
            results = []
            for data in decrypted_data:
                try:
                    results.append(json.loads(data.decode()))
                except Exception as e:
                    self.logger.error(f"Failed to parse decrypted data: {str(e)}")
                    results.append({})
            
            self.metrics.batch_operations += 1
            return results
            
        finally:
            self._record_operation_time(time.time() - start_time)
    
    async def optimized_credential_retrieval(self, credential_ids: List[str], 
                                           user_id: str, master_password: str) -> Dict[str, Optional[Dict[str, Any]]]:
        """Optimized retrieval of multiple credentials"""
        start_time = time.time()
        results = {}
        
        try:
            # Check cache for each credential
            cached_credentials = {}
            uncached_ids = []
            
            for cred_id in credential_ids:
                cached = await self.get_cached_credential(cred_id, user_id)
                if cached:
                    cached_credentials[cred_id] = cached
                else:
                    uncached_ids.append(cred_id)
            
            # Batch retrieve uncached credentials
            if uncached_ids:
                # Get metadata for uncached credentials
                metadata_tasks = []
                for cred_id in uncached_ids:
                    metadata_tasks.append(self.database_manager.retrieve_credential_metadata(cred_id))
                
                metadata_results = await asyncio.gather(*metadata_tasks, return_exceptions=True)
                
                # Get encrypted data for valid credentials
                encrypted_tasks = []
                valid_metadata = {}
                for i, metadata in enumerate(metadata_results):
                    if not isinstance(metadata, Exception) and metadata:
                        cred_id = uncached_ids[i]
                        valid_metadata[cred_id] = metadata
                        encrypted_tasks.append(self.database_manager.retrieve_encrypted_credential(cred_id))
                
                if encrypted_tasks:
                    encrypted_results = await asyncio.gather(*encrypted_tasks, return_exceptions=True)
                    
                    # Batch decrypt
                    decrypt_list = []
                    decrypt_mapping = {}
                    
                    for i, encrypted_data in enumerate(encrypted_results):
                        if not isinstance(encrypted_data, Exception) and encrypted_data:
                            cred_id = list(valid_metadata.keys())[i]
                            # Convert to EncryptedData object
                            encrypted_obj = EncryptedData(
                                ciphertext=encrypted_data[0],
                                algorithm=self.encryption_engine.params.algorithm,
                                key_derivation=self.encryption_engine.params.key_derivation,
                                salt=encrypted_data[2],
                                nonce=encrypted_data[3],
                                tag=encrypted_data[4],
                                key_version=encrypted_data[1],
                                created_at=datetime.utcnow(),
                                metadata={}
                            )
                            decrypt_list.append((encrypted_obj, master_password))
                            decrypt_mapping[len(decrypt_list) - 1] = cred_id
                    
                    if decrypt_list:
                        decrypted_results = await self.batch_decrypt_credentials(decrypt_list)
                        
                        # Cache and store results
                        for i, decrypted_data in enumerate(decrypted_results):
                            if decrypted_data:
                                cred_id = decrypt_mapping[i]
                                results[cred_id] = decrypted_data
                                
                                # Cache for future use
                                await self.cache_credential(cred_id, user_id, decrypted_data)
            
            # Combine cached and newly retrieved results
            results.update(cached_credentials)
            
            # Fill in None for any missing credentials
            for cred_id in credential_ids:
                if cred_id not in results:
                    results[cred_id] = None
            
            return results
            
        finally:
            self._record_operation_time(time.time() - start_time)
    
    async def preload_frequently_accessed(self, user_id: str, limit: int = 50) -> int:
        """Preload frequently accessed credentials for user"""
        try:
            # This would query the database for frequently accessed credentials
            # and preload their metadata into cache
            
            # Placeholder implementation
            frequent_creds = []  # Would come from database query
            
            preloaded = 0
            for cred_id in frequent_creds[:limit]:
                metadata = await self.database_manager.retrieve_credential_metadata(cred_id)
                if metadata:
                    await self.cache_metadata(cred_id, metadata.__dict__)
                    preloaded += 1
            
            return preloaded
            
        except Exception as e:
            self.logger.error(f"Failed to preload credentials: {str(e)}")
            return 0
    
    def _record_operation_time(self, duration: float):
        """Record operation time for metrics"""
        self.operation_times.append(duration)
        self.metrics.total_operations += 1
        
        # Update average response time
        if self.operation_times:
            self.metrics.avg_response_time = sum(self.operation_times) / len(self.operation_times)
    
    async def _cache_cleanup_task(self):
        """Background task to clean up expired cache entries"""
        while True:
            try:
                # Clean up memory caches
                # This would be implemented in the cache classes
                
                await asyncio.sleep(300)  # Run every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Cache cleanup error: {str(e)}")
                await asyncio.sleep(60)
    
    async def _metrics_update_task(self):
        """Background task to update performance metrics"""
        while True:
            try:
                # Update memory usage
                import psutil
                process = psutil.Process()
                self.metrics.memory_usage = process.memory_info().rss
                
                # Update cache statistics
                metadata_stats = await self.metadata_cache.get_stats()
                credential_stats = await self.credential_cache.get_stats()
                
                # Log metrics periodically
                self.logger.debug(f"Performance metrics: {self.metrics}")
                
                await asyncio.sleep(60)  # Update every minute
                
            except Exception as e:
                self.logger.error(f"Metrics update error: {str(e)}")
                await asyncio.sleep(60)
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        try:
            metadata_stats = await self.metadata_cache.get_stats()
            credential_stats = await self.credential_cache.get_stats()
            
            return {
                'metrics': {
                    'cache_hits': self.metrics.cache_hits,
                    'cache_misses': self.metrics.cache_misses,
                    'cache_hit_ratio': (
                        self.metrics.cache_hits / max(1, self.metrics.cache_hits + self.metrics.cache_misses)
                    ),
                    'batch_operations': self.metrics.batch_operations,
                    'avg_response_time': self.metrics.avg_response_time,
                    'total_operations': self.metrics.total_operations,
                    'memory_usage': self.metrics.memory_usage
                },
                'caches': {
                    'metadata': metadata_stats,
                    'credentials': credential_stats
                },
                'recent_operation_times': list(self.operation_times)[-10:],  # Last 10 operations
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get performance stats: {str(e)}")
            return {'error': str(e)}
    
    async def optimize_for_user(self, user_id: str) -> Dict[str, Any]:
        """Optimize performance for specific user"""
        try:
            optimization_results = {}
            
            # Preload frequently accessed credentials
            preloaded = await self.preload_frequently_accessed(user_id)
            optimization_results['preloaded_credentials'] = preloaded
            
            # Clear old cache entries for this user
            # This would involve scanning cache keys and removing old entries
            
            # Warm up connection pool if needed
            # This would ensure database connections are ready
            
            return optimization_results
            
        except Exception as e:
            self.logger.error(f"User optimization failed: {str(e)}")
            return {'error': str(e)}