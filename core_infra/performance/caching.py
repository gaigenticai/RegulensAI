"""
Regulens AI - Advanced Caching Strategy
Multi-tier caching with intelligent invalidation and cache warming strategies.
"""

import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Callable, Set
from enum import Enum
from dataclasses import dataclass
import structlog

from core_infra.config import get_settings
from core_infra.database.connection import get_database
from core_infra.performance.optimization import performance_optimizer

# Initialize logging
logger = structlog.get_logger(__name__)
settings = get_settings()

class CacheLevel(Enum):
    """Cache level enumeration."""
    L1_MEMORY = "l1_memory"
    L2_REDIS = "l2_redis"
    L3_DATABASE = "l3_database"

class CacheStrategy(Enum):
    """Cache strategy enumeration."""
    WRITE_THROUGH = "write_through"
    WRITE_BACK = "write_back"
    WRITE_AROUND = "write_around"
    READ_THROUGH = "read_through"

@dataclass
class CachePolicy:
    """Cache policy configuration."""
    ttl: int = 300
    max_size: int = 1000
    strategy: CacheStrategy = CacheStrategy.READ_THROUGH
    auto_refresh: bool = False
    refresh_threshold: float = 0.8  # Refresh when TTL is 80% expired
    compression: bool = True
    encryption: bool = False

class IntelligentCacheManager:
    """Advanced cache manager with intelligent strategies."""
    
    def __init__(self):
        self.cache_policies = {}
        self.cache_dependencies = {}
        self.access_patterns = {}
        self.invalidation_queue = asyncio.Queue()
        self.warming_tasks = set()
        
    async def initialize(self):
        """Initialize cache manager."""
        try:
            await self._load_cache_policies()
            await self._setup_invalidation_processor()
            await self._setup_cache_warming()
            logger.info("Intelligent cache manager initialized")
        except Exception as e:
            logger.error(f"Cache manager initialization failed: {e}")
            raise
    
    async def _load_cache_policies(self):
        """Load cache policies for different data types."""
        self.cache_policies = {
            # User and authentication data
            'user_profile': CachePolicy(
                ttl=1800,  # 30 minutes
                strategy=CacheStrategy.WRITE_THROUGH,
                auto_refresh=True
            ),
            'user_permissions': CachePolicy(
                ttl=900,  # 15 minutes
                strategy=CacheStrategy.WRITE_THROUGH,
                auto_refresh=True
            ),
            'user_sessions': CachePolicy(
                ttl=300,  # 5 minutes
                strategy=CacheStrategy.WRITE_THROUGH
            ),
            
            # Customer data
            'customer_profile': CachePolicy(
                ttl=3600,  # 1 hour
                strategy=CacheStrategy.READ_THROUGH,
                auto_refresh=True,
                encryption=True
            ),
            'customer_risk_score': CachePolicy(
                ttl=1800,  # 30 minutes
                strategy=CacheStrategy.WRITE_THROUGH,
                auto_refresh=True
            ),
            'customer_screening': CachePolicy(
                ttl=7200,  # 2 hours
                strategy=CacheStrategy.READ_THROUGH
            ),
            
            # Compliance data
            'compliance_programs': CachePolicy(
                ttl=7200,  # 2 hours
                strategy=CacheStrategy.READ_THROUGH,
                auto_refresh=True
            ),
            'compliance_requirements': CachePolicy(
                ttl=3600,  # 1 hour
                strategy=CacheStrategy.READ_THROUGH,
                auto_refresh=True
            ),
            'regulatory_rules': CachePolicy(
                ttl=14400,  # 4 hours
                strategy=CacheStrategy.READ_THROUGH
            ),
            
            # Transaction data
            'transaction_details': CachePolicy(
                ttl=1800,  # 30 minutes
                strategy=CacheStrategy.READ_THROUGH,
                encryption=True
            ),
            'transaction_risk': CachePolicy(
                ttl=900,  # 15 minutes
                strategy=CacheStrategy.WRITE_THROUGH
            ),
            
            # Reports and analytics
            'dashboard_metrics': CachePolicy(
                ttl=300,  # 5 minutes
                strategy=CacheStrategy.READ_THROUGH,
                auto_refresh=True
            ),
            'compliance_reports': CachePolicy(
                ttl=7200,  # 2 hours
                strategy=CacheStrategy.READ_THROUGH
            ),
            'analytics_data': CachePolicy(
                ttl=1800,  # 30 minutes
                strategy=CacheStrategy.READ_THROUGH,
                auto_refresh=True
            ),
            
            # AI and ML data
            'ai_model_results': CachePolicy(
                ttl=3600,  # 1 hour
                strategy=CacheStrategy.READ_THROUGH
            ),
            'risk_predictions': CachePolicy(
                ttl=1800,  # 30 minutes
                strategy=CacheStrategy.WRITE_THROUGH,
                auto_refresh=True
            ),
            
            # Configuration data
            'tenant_settings': CachePolicy(
                ttl=7200,  # 2 hours
                strategy=CacheStrategy.WRITE_THROUGH,
                auto_refresh=True
            ),
            'system_config': CachePolicy(
                ttl=14400,  # 4 hours
                strategy=CacheStrategy.READ_THROUGH
            )
        }
        
        # Setup cache dependencies
        self.cache_dependencies = {
            'user_profile': ['user_permissions', 'user_sessions'],
            'customer_profile': ['customer_risk_score', 'customer_screening'],
            'compliance_programs': ['compliance_requirements'],
            'tenant_settings': ['user_profile', 'compliance_programs']
        }
    
    async def _setup_invalidation_processor(self):
        """Setup background invalidation processor."""
        asyncio.create_task(self._process_invalidations())
    
    async def _setup_cache_warming(self):
        """Setup cache warming strategies."""
        asyncio.create_task(self._cache_warming_loop())
    
    async def get_cached_data(self, cache_type: str, key: str, 
                            loader_func: Optional[Callable] = None) -> Any:
        """Get data from cache with intelligent loading."""
        try:
            policy = self.cache_policies.get(cache_type)
            if not policy:
                logger.warning(f"No cache policy found for type: {cache_type}")
                if loader_func:
                    return await loader_func()
                return None
            
            cache_key = f"{cache_type}:{key}"
            
            # Track access pattern
            await self._track_access(cache_key)
            
            # Try to get from cache
            cached_data = await performance_optimizer.cache.get(cache_key)
            
            if cached_data is not None:
                # Check if auto-refresh is needed
                if policy.auto_refresh and await self._needs_refresh(cache_key, policy):
                    asyncio.create_task(self._refresh_cache_entry(cache_key, loader_func, policy))
                
                return cached_data
            
            # Cache miss - load data if loader provided
            if loader_func:
                data = await loader_func()
                if data is not None:
                    await self._store_in_cache(cache_key, data, policy)
                return data
            
            return None
            
        except Exception as e:
            logger.error(f"Cache get error for {cache_type}:{key}: {e}")
            if loader_func:
                return await loader_func()
            return None
    
    async def set_cached_data(self, cache_type: str, key: str, data: Any) -> bool:
        """Set data in cache with policy enforcement."""
        try:
            policy = self.cache_policies.get(cache_type)
            if not policy:
                return False
            
            cache_key = f"{cache_type}:{key}"
            
            # Store in cache
            success = await self._store_in_cache(cache_key, data, policy)
            
            # Handle write strategies
            if policy.strategy == CacheStrategy.WRITE_THROUGH:
                # Invalidate dependent caches
                await self._invalidate_dependencies(cache_type)
            
            return success
            
        except Exception as e:
            logger.error(f"Cache set error for {cache_type}:{key}: {e}")
            return False
    
    async def invalidate_cache(self, cache_type: str, key: Optional[str] = None):
        """Invalidate cache entries."""
        try:
            if key:
                cache_key = f"{cache_type}:{key}"
                await performance_optimizer.cache.delete(cache_key)
            else:
                # Invalidate all entries of this type
                pattern = f"{cache_type}:*"
                await performance_optimizer.cache.clear_pattern(pattern)
            
            # Queue dependent invalidations
            await self.invalidation_queue.put({
                'type': 'dependency',
                'cache_type': cache_type,
                'key': key
            })
            
        except Exception as e:
            logger.error(f"Cache invalidation error for {cache_type}:{key}: {e}")
    
    async def _store_in_cache(self, cache_key: str, data: Any, policy: CachePolicy) -> bool:
        """Store data in cache with policy enforcement."""
        try:
            # Apply compression if enabled
            if policy.compression and isinstance(data, (dict, list)):
                # JSON compression would be implemented here
                pass
            
            # Apply encryption if enabled
            if policy.encryption:
                # Data encryption would be implemented here
                pass
            
            return await performance_optimizer.cache.set(cache_key, data, policy.ttl)
            
        except Exception as e:
            logger.error(f"Cache store error: {e}")
            return False
    
    async def _track_access(self, cache_key: str):
        """Track cache access patterns."""
        now = datetime.utcnow()
        
        if cache_key not in self.access_patterns:
            self.access_patterns[cache_key] = {
                'count': 0,
                'last_access': now,
                'access_frequency': 0
            }
        
        pattern = self.access_patterns[cache_key]
        pattern['count'] += 1
        
        # Calculate access frequency (accesses per hour)
        time_diff = (now - pattern['last_access']).total_seconds() / 3600
        if time_diff > 0:
            pattern['access_frequency'] = pattern['count'] / time_diff
        
        pattern['last_access'] = now
    
    async def _needs_refresh(self, cache_key: str, policy: CachePolicy) -> bool:
        """Check if cache entry needs refresh."""
        try:
            # This would check TTL remaining and refresh threshold
            # For now, return False (no refresh needed)
            return False
        except Exception:
            return False
    
    async def _refresh_cache_entry(self, cache_key: str, loader_func: Callable, 
                                 policy: CachePolicy):
        """Refresh cache entry in background."""
        try:
            if loader_func:
                fresh_data = await loader_func()
                if fresh_data is not None:
                    await self._store_in_cache(cache_key, fresh_data, policy)
                    logger.debug(f"Cache entry refreshed: {cache_key}")
        except Exception as e:
            logger.error(f"Cache refresh error for {cache_key}: {e}")
    
    async def _invalidate_dependencies(self, cache_type: str):
        """Invalidate dependent cache entries."""
        dependencies = self.cache_dependencies.get(cache_type, [])
        for dep_type in dependencies:
            await self.invalidation_queue.put({
                'type': 'invalidate',
                'cache_type': dep_type
            })
    
    async def _process_invalidations(self):
        """Process cache invalidation queue."""
        while True:
            try:
                invalidation = await self.invalidation_queue.get()
                
                if invalidation['type'] == 'invalidate':
                    pattern = f"{invalidation['cache_type']}:*"
                    await performance_optimizer.cache.clear_pattern(pattern)
                    logger.debug(f"Invalidated cache pattern: {pattern}")
                
                elif invalidation['type'] == 'dependency':
                    await self._invalidate_dependencies(invalidation['cache_type'])
                
                self.invalidation_queue.task_done()
                
            except Exception as e:
                logger.error(f"Invalidation processing error: {e}")
                await asyncio.sleep(1)
    
    async def _cache_warming_loop(self):
        """Background cache warming loop."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                await self._warm_frequently_accessed_data()
            except Exception as e:
                logger.error(f"Cache warming loop error: {e}")
    
    async def _warm_frequently_accessed_data(self):
        """Warm cache with frequently accessed data."""
        try:
            # Identify frequently accessed patterns
            frequent_patterns = []
            for cache_key, pattern in self.access_patterns.items():
                if pattern['access_frequency'] > 10:  # More than 10 accesses per hour
                    frequent_patterns.append(cache_key)
            
            # Warm high-frequency cache entries
            for cache_key in frequent_patterns[:20]:  # Limit to top 20
                if cache_key not in self.warming_tasks:
                    task = asyncio.create_task(self._warm_cache_key(cache_key))
                    self.warming_tasks.add(task)
                    task.add_done_callback(self.warming_tasks.discard)
            
        except Exception as e:
            logger.error(f"Cache warming error: {e}")
    
    async def _warm_cache_key(self, cache_key: str):
        """Warm specific cache key."""
        try:
            # Check if key exists in cache
            cached_data = await performance_optimizer.cache.get(cache_key)
            if cached_data is None:
                # Key not in cache, would need to load from source
                # Implementation depends on cache key type
                pass
        except Exception as e:
            logger.error(f"Cache warming error for {cache_key}: {e}")
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        try:
            base_stats = performance_optimizer.cache.get_stats()
            
            # Add access pattern statistics
            total_accesses = sum(p['count'] for p in self.access_patterns.values())
            avg_frequency = sum(p['access_frequency'] for p in self.access_patterns.values()) / len(self.access_patterns) if self.access_patterns else 0
            
            # Most accessed keys
            most_accessed = sorted(
                self.access_patterns.items(),
                key=lambda x: x[1]['count'],
                reverse=True
            )[:10]
            
            return {
                **base_stats,
                'access_patterns': {
                    'total_keys_tracked': len(self.access_patterns),
                    'total_accesses': total_accesses,
                    'average_frequency': round(avg_frequency, 2),
                    'most_accessed_keys': [
                        {
                            'key': key,
                            'count': pattern['count'],
                            'frequency': round(pattern['access_frequency'], 2)
                        }
                        for key, pattern in most_accessed
                    ]
                },
                'cache_policies': {
                    'total_policies': len(self.cache_policies),
                    'auto_refresh_enabled': sum(1 for p in self.cache_policies.values() if p.auto_refresh),
                    'encrypted_caches': sum(1 for p in self.cache_policies.values() if p.encryption)
                },
                'warming_tasks': len(self.warming_tasks),
                'invalidation_queue_size': self.invalidation_queue.qsize()
            }
            
        except Exception as e:
            logger.error(f"Cache statistics error: {e}")
            return {'error': str(e)}

# Global cache manager instance
cache_manager = IntelligentCacheManager()

# Convenience functions
async def get_cached(cache_type: str, key: str, loader_func: Optional[Callable] = None) -> Any:
    """Convenience function for getting cached data."""
    return await cache_manager.get_cached_data(cache_type, key, loader_func)

async def set_cached(cache_type: str, key: str, data: Any) -> bool:
    """Convenience function for setting cached data."""
    return await cache_manager.set_cached_data(cache_type, key, data)

async def invalidate_cached(cache_type: str, key: Optional[str] = None):
    """Convenience function for invalidating cached data."""
    await cache_manager.invalidate_cache(cache_type, key)

async def get_cache_stats() -> Dict[str, Any]:
    """Convenience function for getting cache statistics."""
    return await cache_manager.get_cache_statistics()

# Cache decorators for specific data types
def cache_user_data(ttl: int = 1800):
    """Decorator for caching user data."""
    return performance_optimizer.cached(ttl, "user_profile")

def cache_customer_data(ttl: int = 3600):
    """Decorator for caching customer data."""
    return performance_optimizer.cached(ttl, "customer_profile")

def cache_compliance_data(ttl: int = 7200):
    """Decorator for caching compliance data."""
    return performance_optimizer.cached(ttl, "compliance_programs")

def cache_analytics_data(ttl: int = 1800):
    """Decorator for caching analytics data."""
    return performance_optimizer.cached(ttl, "analytics_data")
