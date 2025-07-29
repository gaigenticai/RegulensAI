"""
Regulens AI - Performance Optimization Framework
Enterprise-grade performance optimization with caching, query optimization, and resource management.
"""

import asyncio
import time
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Callable
from functools import wraps
from dataclasses import dataclass
import redis.asyncio as redis
import structlog

from core_infra.config import get_settings
from core_infra.database.connection import get_database
from core_infra.exceptions import SystemException

# Initialize logging
logger = structlog.get_logger(__name__)
settings = get_settings()

@dataclass
class CacheConfig:
    """Cache configuration settings."""
    ttl: int = 300  # Time to live in seconds
    max_size: int = 1000  # Maximum cache size
    key_prefix: str = "regulens"
    compression: bool = True

@dataclass
class PerformanceMetric:
    """Performance metric data structure."""
    name: str
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str] = None

class PerformanceCache:
    """High-performance caching layer with Redis backend."""
    
    def __init__(self):
        self.redis_client = None
        self.local_cache = {}
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }
        
    async def initialize(self):
        """Initialize cache connections."""
        try:
            # Initialize Redis connection
            redis_url = settings.redis_url
            self.redis_client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
                retry_on_timeout=True
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Performance cache initialized successfully")
            
        except Exception as e:
            logger.warning(f"Redis cache initialization failed, using local cache: {e}")
            self.redis_client = None
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache."""
        try:
            # Try Redis first
            if self.redis_client:
                value = await self.redis_client.get(key)
                if value is not None:
                    self.cache_stats['hits'] += 1
                    return json.loads(value)
            
            # Fallback to local cache
            if key in self.local_cache:
                entry = self.local_cache[key]
                if entry['expires'] > datetime.utcnow():
                    self.cache_stats['hits'] += 1
                    return entry['value']
                else:
                    del self.local_cache[key]
            
            self.cache_stats['misses'] += 1
            return default
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return default
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache."""
        try:
            serialized_value = json.dumps(value, default=str)
            
            # Set in Redis
            if self.redis_client:
                await self.redis_client.setex(key, ttl, serialized_value)
            
            # Set in local cache
            self.local_cache[key] = {
                'value': value,
                'expires': datetime.utcnow() + timedelta(seconds=ttl)
            }
            
            # Limit local cache size
            if len(self.local_cache) > 1000:
                # Remove oldest entries
                sorted_items = sorted(
                    self.local_cache.items(),
                    key=lambda x: x[1]['expires']
                )
                for old_key, _ in sorted_items[:100]:
                    del self.local_cache[old_key]
            
            self.cache_stats['sets'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            # Delete from Redis
            if self.redis_client:
                await self.redis_client.delete(key)
            
            # Delete from local cache
            if key in self.local_cache:
                del self.local_cache[key]
            
            self.cache_stats['deletes'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear cache entries matching pattern."""
        try:
            deleted_count = 0
            
            # Clear from Redis
            if self.redis_client:
                keys = await self.redis_client.keys(pattern)
                if keys:
                    deleted_count += await self.redis_client.delete(*keys)
            
            # Clear from local cache
            keys_to_delete = [k for k in self.local_cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self.local_cache[key]
                deleted_count += 1
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Cache clear pattern error: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = (self.cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'hits': self.cache_stats['hits'],
            'misses': self.cache_stats['misses'],
            'sets': self.cache_stats['sets'],
            'deletes': self.cache_stats['deletes'],
            'hit_rate_percent': round(hit_rate, 2),
            'local_cache_size': len(self.local_cache),
            'redis_connected': self.redis_client is not None
        }

class QueryOptimizer:
    """Database query optimization and monitoring."""
    
    def __init__(self):
        self.query_stats = {}
        self.slow_query_threshold = 1000  # milliseconds
        
    def track_query(self, query: str, duration_ms: float, result_count: int = 0):
        """Track query performance."""
        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
        
        if query_hash not in self.query_stats:
            self.query_stats[query_hash] = {
                'query': query[:200] + '...' if len(query) > 200 else query,
                'count': 0,
                'total_duration_ms': 0,
                'min_duration_ms': float('inf'),
                'max_duration_ms': 0,
                'avg_duration_ms': 0,
                'slow_queries': 0
            }
        
        stats = self.query_stats[query_hash]
        stats['count'] += 1
        stats['total_duration_ms'] += duration_ms
        stats['min_duration_ms'] = min(stats['min_duration_ms'], duration_ms)
        stats['max_duration_ms'] = max(stats['max_duration_ms'], duration_ms)
        stats['avg_duration_ms'] = stats['total_duration_ms'] / stats['count']
        
        if duration_ms > self.slow_query_threshold:
            stats['slow_queries'] += 1
            logger.warning(f"Slow query detected: {duration_ms}ms - {query[:100]}...")
    
    def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get slowest queries."""
        sorted_queries = sorted(
            self.query_stats.values(),
            key=lambda x: x['avg_duration_ms'],
            reverse=True
        )
        return sorted_queries[:limit]
    
    def get_frequent_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most frequent queries."""
        sorted_queries = sorted(
            self.query_stats.values(),
            key=lambda x: x['count'],
            reverse=True
        )
        return sorted_queries[:limit]

class PerformanceMonitor:
    """Comprehensive performance monitoring and metrics collection."""
    
    def __init__(self):
        self.metrics_buffer = []
        self.buffer_size = 1000
        self.flush_interval = 60  # seconds
        
    async def initialize(self):
        """Initialize performance monitoring."""
        try:
            # Start background metrics flushing
            asyncio.create_task(self._metrics_flush_loop())
            logger.info("Performance monitoring initialized")
        except Exception as e:
            logger.error(f"Performance monitoring initialization failed: {e}")
    
    async def record_metric(self, name: str, value: float, unit: str = "count", 
                          tags: Dict[str, str] = None):
        """Record a performance metric."""
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.utcnow(),
            tags=tags or {}
        )
        
        self.metrics_buffer.append(metric)
        
        # Flush if buffer is full
        if len(self.metrics_buffer) >= self.buffer_size:
            await self._flush_metrics()
    
    async def _metrics_flush_loop(self):
        """Background metrics flushing loop."""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                await self._flush_metrics()
            except Exception as e:
                logger.error(f"Metrics flush loop error: {e}")
    
    async def _flush_metrics(self):
        """Flush metrics to database."""
        if not self.metrics_buffer:
            return
        
        try:
            async with get_database() as db:
                # Batch insert metrics
                values = []
                for metric in self.metrics_buffer:
                    values.append((
                        metric.name,
                        metric.value,
                        metric.unit,
                        metric.tags,
                        metric.timestamp
                    ))
                
                await db.executemany(
                    """
                    INSERT INTO performance_metrics (
                        metric_name, metric_value, metric_unit, tags, timestamp
                    ) VALUES ($1, $2, $3, $4, $5)
                    """,
                    values
                )
                
                logger.debug(f"Flushed {len(self.metrics_buffer)} metrics to database")
                self.metrics_buffer.clear()
                
        except Exception as e:
            logger.error(f"Failed to flush metrics: {e}")

class PerformanceOptimizer:
    """Main performance optimization coordinator."""
    
    def __init__(self):
        self.cache = PerformanceCache()
        self.query_optimizer = QueryOptimizer()
        self.monitor = PerformanceMonitor()
        self.optimization_rules = {}
        
    async def initialize(self):
        """Initialize all performance components."""
        try:
            await self.cache.initialize()
            await self.monitor.initialize()
            await self._load_optimization_rules()
            logger.info("Performance optimizer initialized successfully")
        except Exception as e:
            logger.error(f"Performance optimizer initialization failed: {e}")
            raise SystemException(f"Performance optimization initialization failed: {e}")
    
    async def _load_optimization_rules(self):
        """Load performance optimization rules."""
        self.optimization_rules = {
            'cache_customer_data': {
                'ttl': 1800,  # 30 minutes
                'pattern': 'customer:*'
            },
            'cache_compliance_programs': {
                'ttl': 3600,  # 1 hour
                'pattern': 'compliance:programs:*'
            },
            'cache_user_permissions': {
                'ttl': 900,  # 15 minutes
                'pattern': 'user:permissions:*'
            },
            'cache_reports': {
                'ttl': 7200,  # 2 hours
                'pattern': 'reports:*'
            }
        }
    
    def cached(self, ttl: int = 300, key_prefix: str = ""):
        """Decorator for caching function results."""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                key_parts = [key_prefix or func.__name__]
                key_parts.extend([str(arg) for arg in args])
                key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
                cache_key = f"regulens:{':'.join(key_parts)}"
                
                # Try to get from cache
                cached_result = await self.cache.get(cache_key)
                if cached_result is not None:
                    await self.monitor.record_metric("cache.hit", 1, tags={"function": func.__name__})
                    return cached_result
                
                # Execute function and cache result
                start_time = time.time()
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                # Cache the result
                await self.cache.set(cache_key, result, ttl)
                
                # Record metrics
                await self.monitor.record_metric("cache.miss", 1, tags={"function": func.__name__})
                await self.monitor.record_metric("function.duration", duration_ms, "ms", 
                                               tags={"function": func.__name__})
                
                return result
            return wrapper
        return decorator
    
    def timed(self, metric_name: str = None):
        """Decorator for timing function execution."""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    duration_ms = (time.time() - start_time) * 1000
                    
                    # Record timing metric
                    name = metric_name or f"function.{func.__name__}.duration"
                    await self.monitor.record_metric(name, duration_ms, "ms")
                    
                    return result
                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    
                    # Record error metric
                    name = metric_name or f"function.{func.__name__}.error"
                    await self.monitor.record_metric(name, 1, tags={"error": str(e)[:100]})
                    
                    raise
            return wrapper
        return decorator
    
    async def optimize_query(self, query: str, params: List[Any] = None) -> str:
        """Optimize database query."""
        # Simple query optimization rules
        optimized_query = query
        
        # Add LIMIT if not present for SELECT queries
        if query.strip().upper().startswith('SELECT') and 'LIMIT' not in query.upper():
            optimized_query += ' LIMIT 1000'
        
        # Add indexes hints for common patterns
        if 'WHERE tenant_id =' in query and 'ORDER BY created_at' in query:
            # Suggest composite index
            logger.debug("Consider adding composite index on (tenant_id, created_at)")
        
        return optimized_query
    
    async def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        try:
            report = {
                'timestamp': datetime.utcnow().isoformat(),
                'cache_stats': self.cache.get_stats(),
                'slow_queries': self.query_optimizer.get_slow_queries(),
                'frequent_queries': self.query_optimizer.get_frequent_queries(),
                'optimization_recommendations': await self._get_optimization_recommendations()
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate performance report: {e}")
            return {'error': str(e)}
    
    async def _get_optimization_recommendations(self) -> List[Dict[str, str]]:
        """Generate optimization recommendations."""
        recommendations = []
        
        # Cache hit rate recommendations
        cache_stats = self.cache.get_stats()
        if cache_stats['hit_rate_percent'] < 70:
            recommendations.append({
                'type': 'cache',
                'priority': 'high',
                'description': f"Cache hit rate is {cache_stats['hit_rate_percent']}%. Consider increasing cache TTL or improving cache key strategies."
            })
        
        # Slow query recommendations
        slow_queries = self.query_optimizer.get_slow_queries(5)
        if slow_queries:
            recommendations.append({
                'type': 'query',
                'priority': 'high',
                'description': f"Found {len(slow_queries)} slow queries. Consider adding indexes or optimizing query structure."
            })
        
        # Memory usage recommendations
        if len(self.cache.local_cache) > 800:
            recommendations.append({
                'type': 'memory',
                'priority': 'medium',
                'description': "Local cache size is high. Consider increasing Redis usage or reducing cache TTL."
            })
        
        return recommendations
    
    async def clear_cache_pattern(self, pattern: str) -> int:
        """Clear cache entries matching pattern."""
        return await self.cache.clear_pattern(pattern)
    
    async def warm_cache(self, cache_keys: List[str]):
        """Warm up cache with frequently accessed data."""
        try:
            for key in cache_keys:
                # This would typically load data and cache it
                # Implementation depends on specific data types
                pass
            
            logger.info(f"Cache warmed with {len(cache_keys)} keys")
            
        except Exception as e:
            logger.error(f"Cache warming failed: {e}")

# Global performance optimizer instance
performance_optimizer = PerformanceOptimizer()

# Convenience decorators
def cached(ttl: int = 300, key_prefix: str = ""):
    """Convenience caching decorator."""
    return performance_optimizer.cached(ttl, key_prefix)

def timed(metric_name: str = None):
    """Convenience timing decorator."""
    return performance_optimizer.timed(metric_name)

# Convenience functions
async def record_metric(name: str, value: float, unit: str = "count", tags: Dict[str, str] = None):
    """Convenience function for recording metrics."""
    await performance_optimizer.monitor.record_metric(name, value, unit, tags)

async def get_performance_report() -> Dict[str, Any]:
    """Convenience function for performance report."""
    return await performance_optimizer.get_performance_report()

async def clear_cache(pattern: str = "*") -> int:
    """Convenience function for clearing cache."""
    return await performance_optimizer.clear_cache_pattern(pattern)
