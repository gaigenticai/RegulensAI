"""
Redis Cache Manager for RegulensAI Performance Optimization.
Implements intelligent caching strategies for external API responses and database queries.
"""

import asyncio
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Callable
from functools import wraps
import structlog
import redis.asyncio as redis
from dataclasses import dataclass, asdict
import pickle
import zlib

logger = structlog.get_logger(__name__)


@dataclass
class CacheConfig:
    """Cache configuration for different data types."""
    ttl_seconds: int
    max_size_mb: int
    compression_enabled: bool = True
    serialization_format: str = "json"  # json, pickle
    eviction_policy: str = "lru"  # lru, lfu, ttl
    namespace: str = "regulensai"


class RedisCacheManager:
    """
    Advanced Redis cache manager with intelligent caching strategies.
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        default_ttl: int = 3600,
        max_memory_mb: int = 1024
    ):
        self.redis = redis_client
        self.default_ttl = default_ttl
        self.max_memory_mb = max_memory_mb
        
        # Cache configurations for different data types
        self.cache_configs = {
            "external_api": CacheConfig(
                ttl_seconds=1800,  # 30 minutes
                max_size_mb=256,
                compression_enabled=True,
                serialization_format="json"
            ),
            "database_query": CacheConfig(
                ttl_seconds=300,   # 5 minutes
                max_size_mb=128,
                compression_enabled=True,
                serialization_format="pickle"
            ),
            "entity_screening": CacheConfig(
                ttl_seconds=3600,  # 1 hour
                max_size_mb=512,
                compression_enabled=True,
                serialization_format="json"
            ),
            "user_session": CacheConfig(
                ttl_seconds=86400, # 24 hours
                max_size_mb=64,
                compression_enabled=False,
                serialization_format="json"
            ),
            "feature_flags": CacheConfig(
                ttl_seconds=300,   # 5 minutes
                max_size_mb=16,
                compression_enabled=False,
                serialization_format="json"
            ),
            "notification_templates": CacheConfig(
                ttl_seconds=1800,  # 30 minutes
                max_size_mb=32,
                compression_enabled=True,
                serialization_format="json"
            )
        }
        
        # Performance metrics
        self.metrics = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0
        }
    
    async def get(
        self,
        key: str,
        cache_type: str = "default",
        deserialize: bool = True
    ) -> Optional[Any]:
        """
        Get value from cache with automatic deserialization.
        """
        try:
            cache_key = self._build_cache_key(key, cache_type)
            
            # Get from Redis
            cached_data = await self.redis.get(cache_key)
            
            if cached_data is None:
                self.metrics["misses"] += 1
                return None
            
            self.metrics["hits"] += 1
            
            if not deserialize:
                return cached_data
            
            # Deserialize based on cache configuration
            config = self.cache_configs.get(cache_type, self.cache_configs["external_api"])
            return self._deserialize(cached_data, config)
            
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            self.metrics["errors"] += 1
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        cache_type: str = "default",
        ttl: Optional[int] = None,
        serialize: bool = True
    ) -> bool:
        """
        Set value in cache with automatic serialization and compression.
        """
        try:
            cache_key = self._build_cache_key(key, cache_type)
            config = self.cache_configs.get(cache_type, self.cache_configs["external_api"])
            
            # Serialize data
            if serialize:
                serialized_data = self._serialize(value, config)
            else:
                serialized_data = value
            
            # Set TTL
            cache_ttl = ttl or config.ttl_seconds
            
            # Store in Redis
            await self.redis.setex(cache_key, cache_ttl, serialized_data)
            
            self.metrics["sets"] += 1
            
            # Update cache metadata
            await self._update_cache_metadata(cache_key, cache_type, len(serialized_data))
            
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            self.metrics["errors"] += 1
            return False
    
    async def delete(self, key: str, cache_type: str = "default") -> bool:
        """Delete value from cache."""
        try:
            cache_key = self._build_cache_key(key, cache_type)
            result = await self.redis.delete(cache_key)
            
            if result:
                self.metrics["deletes"] += 1
                await self._remove_cache_metadata(cache_key, cache_type)
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            self.metrics["errors"] += 1
            return False
    
    async def exists(self, key: str, cache_type: str = "default") -> bool:
        """Check if key exists in cache."""
        try:
            cache_key = self._build_cache_key(key, cache_type)
            return bool(await self.redis.exists(cache_key))
            
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    async def get_or_set(
        self,
        key: str,
        fetch_function: Callable,
        cache_type: str = "default",
        ttl: Optional[int] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Get value from cache or fetch and cache if not found.
        """
        # Try to get from cache first
        cached_value = await self.get(key, cache_type)
        
        if cached_value is not None:
            return cached_value
        
        # Fetch fresh data
        try:
            if asyncio.iscoroutinefunction(fetch_function):
                fresh_value = await fetch_function(*args, **kwargs)
            else:
                fresh_value = fetch_function(*args, **kwargs)
            
            # Cache the fresh value
            await self.set(key, fresh_value, cache_type, ttl)
            
            return fresh_value
            
        except Exception as e:
            logger.error(f"Error fetching data for cache key {key}: {e}")
            raise
    
    async def invalidate_pattern(self, pattern: str, cache_type: str = "default") -> int:
        """Invalidate all keys matching a pattern."""
        try:
            namespace = self.cache_configs.get(cache_type, self.cache_configs["external_api"]).namespace
            full_pattern = f"{namespace}:{cache_type}:{pattern}"
            
            # Find matching keys
            keys = []
            async for key in self.redis.scan_iter(match=full_pattern):
                keys.append(key)
            
            # Delete keys in batches
            if keys:
                deleted_count = 0
                batch_size = 100
                
                for i in range(0, len(keys), batch_size):
                    batch = keys[i:i + batch_size]
                    deleted_count += await self.redis.delete(*batch)
                
                logger.info(f"Invalidated {deleted_count} cache keys matching pattern {pattern}")
                return deleted_count
            
            return 0
            
        except Exception as e:
            logger.error(f"Error invalidating cache pattern {pattern}: {e}")
            return 0
    
    async def get_cache_stats(self, cache_type: Optional[str] = None) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            stats = {
                "performance_metrics": self.metrics.copy(),
                "hit_ratio": self._calculate_hit_ratio(),
                "cache_types": {}
            }
            
            # Get stats for specific cache type or all types
            cache_types = [cache_type] if cache_type else self.cache_configs.keys()
            
            for ct in cache_types:
                type_stats = await self._get_cache_type_stats(ct)
                stats["cache_types"][ct] = type_stats
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"error": str(e)}
    
    def cache_result(
        self,
        cache_type: str = "default",
        ttl: Optional[int] = None,
        key_generator: Optional[Callable] = None
    ):
        """
        Decorator to cache function results.
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Generate cache key
                if key_generator:
                    cache_key = key_generator(*args, **kwargs)
                else:
                    cache_key = self._generate_function_cache_key(func, *args, **kwargs)
                
                return await self.get_or_set(
                    cache_key,
                    func,
                    cache_type,
                    ttl,
                    *args,
                    **kwargs
                )
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # For sync functions, we need to run in async context
                return asyncio.run(async_wrapper(*args, **kwargs))
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        
        return decorator
    
    async def warm_cache(self, cache_type: str, data_loader: Callable) -> int:
        """
        Warm cache with pre-loaded data.
        """
        try:
            logger.info(f"Starting cache warming for type: {cache_type}")
            
            if asyncio.iscoroutinefunction(data_loader):
                data_items = await data_loader()
            else:
                data_items = data_loader()
            
            warmed_count = 0
            
            for key, value in data_items.items():
                success = await self.set(key, value, cache_type)
                if success:
                    warmed_count += 1
            
            logger.info(f"Cache warming completed: {warmed_count} items loaded for {cache_type}")
            return warmed_count
            
        except Exception as e:
            logger.error(f"Error warming cache for type {cache_type}: {e}")
            return 0
    
    async def cleanup_expired(self, cache_type: Optional[str] = None) -> int:
        """
        Clean up expired cache entries.
        """
        try:
            cleaned_count = 0
            cache_types = [cache_type] if cache_type else self.cache_configs.keys()
            
            for ct in cache_types:
                namespace = self.cache_configs[ct].namespace
                pattern = f"{namespace}:{ct}:*"
                
                async for key in self.redis.scan_iter(match=pattern):
                    ttl = await self.redis.ttl(key)
                    if ttl == -2:  # Key doesn't exist
                        continue
                    elif ttl == -1:  # Key exists but has no expiry
                        # Set expiry based on cache config
                        await self.redis.expire(key, self.cache_configs[ct].ttl_seconds)
                    # Keys with positive TTL are fine
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired cache entries: {e}")
            return 0
    
    def _build_cache_key(self, key: str, cache_type: str) -> str:
        """Build namespaced cache key."""
        config = self.cache_configs.get(cache_type, self.cache_configs["external_api"])
        return f"{config.namespace}:{cache_type}:{key}"
    
    def _serialize(self, data: Any, config: CacheConfig) -> bytes:
        """Serialize data based on configuration."""
        if config.serialization_format == "json":
            serialized = json.dumps(data, default=str).encode('utf-8')
        elif config.serialization_format == "pickle":
            serialized = pickle.dumps(data)
        else:
            raise ValueError(f"Unsupported serialization format: {config.serialization_format}")
        
        # Apply compression if enabled
        if config.compression_enabled:
            serialized = zlib.compress(serialized)
        
        return serialized
    
    def _deserialize(self, data: bytes, config: CacheConfig) -> Any:
        """Deserialize data based on configuration."""
        # Decompress if needed
        if config.compression_enabled:
            data = zlib.decompress(data)
        
        if config.serialization_format == "json":
            return json.loads(data.decode('utf-8'))
        elif config.serialization_format == "pickle":
            return pickle.loads(data)
        else:
            raise ValueError(f"Unsupported serialization format: {config.serialization_format}")
    
    def _generate_function_cache_key(self, func: Callable, *args, **kwargs) -> str:
        """Generate cache key for function calls."""
        # Create a hash of function name and arguments
        func_name = f"{func.__module__}.{func.__name__}"
        
        # Convert args and kwargs to a hashable representation
        args_str = str(args)
        kwargs_str = str(sorted(kwargs.items()))
        
        # Create hash
        key_data = f"{func_name}:{args_str}:{kwargs_str}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _calculate_hit_ratio(self) -> float:
        """Calculate cache hit ratio."""
        total_requests = self.metrics["hits"] + self.metrics["misses"]
        if total_requests == 0:
            return 0.0
        return self.metrics["hits"] / total_requests
    
    async def _update_cache_metadata(self, cache_key: str, cache_type: str, size_bytes: int):
        """Update cache metadata for monitoring."""
        metadata_key = f"metadata:{cache_type}"
        
        # Update size tracking
        await self.redis.hincrby(metadata_key, "total_size_bytes", size_bytes)
        await self.redis.hincrby(metadata_key, "entry_count", 1)
        await self.redis.hset(metadata_key, "last_updated", int(time.time()))
    
    async def _remove_cache_metadata(self, cache_key: str, cache_type: str):
        """Remove cache metadata when entry is deleted."""
        metadata_key = f"metadata:{cache_type}"
        await self.redis.hincrby(metadata_key, "entry_count", -1)
    
    async def _get_cache_type_stats(self, cache_type: str) -> Dict[str, Any]:
        """Get statistics for a specific cache type."""
        metadata_key = f"metadata:{cache_type}"
        metadata = await self.redis.hgetall(metadata_key)
        
        config = self.cache_configs.get(cache_type, self.cache_configs["external_api"])
        
        return {
            "config": asdict(config),
            "entry_count": int(metadata.get(b"entry_count", 0)),
            "total_size_bytes": int(metadata.get(b"total_size_bytes", 0)),
            "last_updated": int(metadata.get(b"last_updated", 0)),
            "max_size_bytes": config.max_size_mb * 1024 * 1024
        }


# Specialized cache managers for different use cases
class ExternalAPICache(RedisCacheManager):
    """Specialized cache for external API responses."""
    
    def __init__(self, redis_client: redis.Redis):
        super().__init__(redis_client)
        
    async def cache_api_response(
        self,
        provider: str,
        endpoint: str,
        params: Dict[str, Any],
        response_data: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Cache external API response."""
        # Generate cache key based on provider, endpoint, and parameters
        params_hash = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()
        cache_key = f"{provider}:{endpoint}:{params_hash}"
        
        return await self.set(cache_key, response_data, "external_api", ttl)
    
    async def get_cached_api_response(
        self,
        provider: str,
        endpoint: str,
        params: Dict[str, Any]
    ) -> Optional[Any]:
        """Get cached external API response."""
        params_hash = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()
        cache_key = f"{provider}:{endpoint}:{params_hash}"
        
        return await self.get(cache_key, "external_api")


class DatabaseQueryCache(RedisCacheManager):
    """Specialized cache for database query results."""
    
    def __init__(self, redis_client: redis.Redis):
        super().__init__(redis_client)
    
    async def cache_query_result(
        self,
        query_hash: str,
        result: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Cache database query result."""
        return await self.set(query_hash, result, "database_query", ttl)
    
    async def get_cached_query_result(self, query_hash: str) -> Optional[Any]:
        """Get cached database query result."""
        return await self.get(query_hash, "database_query")
    
    def cache_query(self, ttl: Optional[int] = None):
        """Decorator to cache database query results."""
        return self.cache_result("database_query", ttl)


# Global cache manager instances
cache_manager = None
external_api_cache = None
database_query_cache = None


async def initialize_cache_managers(redis_client: redis.Redis):
    """Initialize global cache manager instances."""
    global cache_manager, external_api_cache, database_query_cache
    
    cache_manager = RedisCacheManager(redis_client)
    external_api_cache = ExternalAPICache(redis_client)
    database_query_cache = DatabaseQueryCache(redis_client)
    
    logger.info("Cache managers initialized successfully")


def get_cache_manager() -> Optional[RedisCacheManager]:
    """Get the global cache manager instance."""
    return cache_manager
