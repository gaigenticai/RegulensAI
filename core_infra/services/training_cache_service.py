"""
Training Portal Cache Service
Implements comprehensive caching strategies for training portal performance optimization.
"""

import json
import hashlib
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from functools import wraps
import asyncio
import structlog

from core_infra.utils.cache import CacheManager, cache_key_builder
from core_infra.database.models import TrainingModule, TrainingEnrollment, User
from core_infra.config import settings

logger = structlog.get_logger(__name__)


class TrainingCacheService:
    """Advanced caching service for training portal with intelligent cache management."""
    
    def __init__(self):
        self.cache_manager = CacheManager()
        self.default_ttl = 3600  # 1 hour
        self.short_ttl = 300     # 5 minutes
        self.long_ttl = 86400    # 24 hours
        
        # Cache key prefixes
        self.prefixes = {
            'module': 'training:module',
            'enrollment': 'training:enrollment',
            'progress': 'training:progress',
            'analytics': 'training:analytics',
            'search': 'training:search',
            'recommendations': 'training:recommendations',
            'certificates': 'training:certificates',
            'user_data': 'training:user'
        }
    
    def _build_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Build a standardized cache key."""
        key_parts = [self.prefixes.get(prefix, prefix)]
        key_parts.extend(str(arg) for arg in args)
        
        if kwargs:
            # Sort kwargs for consistent key generation
            sorted_kwargs = sorted(kwargs.items())
            key_parts.append(hashlib.md5(
                json.dumps(sorted_kwargs, sort_keys=True).encode()
            ).hexdigest()[:8])
        
        return ':'.join(key_parts)
    
    async def get_cached_modules(
        self, 
        tenant_id: str, 
        filters: Dict[str, Any] = None,
        page: int = 1,
        size: int = 20
    ) -> Optional[Dict[str, Any]]:
        """Get cached training modules with filters."""
        try:
            cache_key = self._build_cache_key(
                'module', 'list', tenant_id, 
                page=page, size=size, filters=filters or {}
            )
            
            cached_data = await self.cache_manager.get(cache_key)
            if cached_data:
                logger.debug("Cache hit for modules", cache_key=cache_key)
                return json.loads(cached_data)
            
            return None
            
        except Exception as e:
            logger.error("Failed to get cached modules", error=str(e))
            return None
    
    async def cache_modules(
        self,
        tenant_id: str,
        modules_data: Dict[str, Any],
        filters: Dict[str, Any] = None,
        page: int = 1,
        size: int = 20,
        ttl: int = None
    ) -> bool:
        """Cache training modules data."""
        try:
            cache_key = self._build_cache_key(
                'module', 'list', tenant_id,
                page=page, size=size, filters=filters or {}
            )
            
            # Add cache metadata
            cached_data = {
                **modules_data,
                'cached_at': datetime.utcnow().isoformat(),
                'cache_key': cache_key
            }
            
            success = await self.cache_manager.set(
                cache_key,
                json.dumps(cached_data, default=str),
                ttl or self.default_ttl
            )
            
            if success:
                logger.debug("Cached modules data", cache_key=cache_key)
            
            return success
            
        except Exception as e:
            logger.error("Failed to cache modules", error=str(e))
            return False
    
    async def get_cached_module(self, module_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get cached individual module data."""
        try:
            cache_key = self._build_cache_key('module', 'detail', module_id, tenant_id)
            cached_data = await self.cache_manager.get(cache_key)
            
            if cached_data:
                logger.debug("Cache hit for module", module_id=module_id)
                return json.loads(cached_data)
            
            return None
            
        except Exception as e:
            logger.error("Failed to get cached module", module_id=module_id, error=str(e))
            return None
    
    async def cache_module(
        self, 
        module_id: str, 
        tenant_id: str, 
        module_data: Dict[str, Any],
        ttl: int = None
    ) -> bool:
        """Cache individual module data."""
        try:
            cache_key = self._build_cache_key('module', 'detail', module_id, tenant_id)
            
            cached_data = {
                **module_data,
                'cached_at': datetime.utcnow().isoformat()
            }
            
            success = await self.cache_manager.set(
                cache_key,
                json.dumps(cached_data, default=str),
                ttl or self.long_ttl  # Modules change less frequently
            )
            
            if success:
                logger.debug("Cached module data", module_id=module_id)
            
            return success
            
        except Exception as e:
            logger.error("Failed to cache module", module_id=module_id, error=str(e))
            return False
    
    async def get_cached_user_enrollments(self, user_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached user enrollments."""
        try:
            cache_key = self._build_cache_key('enrollment', 'user', user_id)
            cached_data = await self.cache_manager.get(cache_key)
            
            if cached_data:
                logger.debug("Cache hit for user enrollments", user_id=user_id)
                return json.loads(cached_data)
            
            return None
            
        except Exception as e:
            logger.error("Failed to get cached enrollments", user_id=user_id, error=str(e))
            return None
    
    async def cache_user_enrollments(
        self, 
        user_id: str, 
        enrollments_data: List[Dict[str, Any]],
        ttl: int = None
    ) -> bool:
        """Cache user enrollments."""
        try:
            cache_key = self._build_cache_key('enrollment', 'user', user_id)
            
            cached_data = {
                'enrollments': enrollments_data,
                'cached_at': datetime.utcnow().isoformat(),
                'user_id': user_id
            }
            
            success = await self.cache_manager.set(
                cache_key,
                json.dumps(cached_data, default=str),
                ttl or self.short_ttl  # Enrollments change more frequently
            )
            
            if success:
                logger.debug("Cached user enrollments", user_id=user_id)
            
            return success
            
        except Exception as e:
            logger.error("Failed to cache enrollments", user_id=user_id, error=str(e))
            return False
    
    async def get_cached_progress(self, enrollment_id: str) -> Optional[Dict[str, Any]]:
        """Get cached enrollment progress."""
        try:
            cache_key = self._build_cache_key('progress', enrollment_id)
            cached_data = await self.cache_manager.get(cache_key)
            
            if cached_data:
                logger.debug("Cache hit for progress", enrollment_id=enrollment_id)
                return json.loads(cached_data)
            
            return None
            
        except Exception as e:
            logger.error("Failed to get cached progress", enrollment_id=enrollment_id, error=str(e))
            return None
    
    async def cache_progress(
        self, 
        enrollment_id: str, 
        progress_data: Dict[str, Any],
        ttl: int = None
    ) -> bool:
        """Cache enrollment progress."""
        try:
            cache_key = self._build_cache_key('progress', enrollment_id)
            
            cached_data = {
                **progress_data,
                'cached_at': datetime.utcnow().isoformat()
            }
            
            success = await self.cache_manager.set(
                cache_key,
                json.dumps(cached_data, default=str),
                ttl or self.short_ttl  # Progress changes frequently
            )
            
            if success:
                logger.debug("Cached progress data", enrollment_id=enrollment_id)
            
            return success
            
        except Exception as e:
            logger.error("Failed to cache progress", enrollment_id=enrollment_id, error=str(e))
            return False
    
    async def invalidate_user_cache(self, user_id: str) -> bool:
        """Invalidate all cache entries for a user."""
        try:
            patterns = [
                f"{self.prefixes['enrollment']}:user:{user_id}*",
                f"{self.prefixes['progress']}:*",  # Progress might be affected
                f"{self.prefixes['user_data']}:{user_id}*",
                f"{self.prefixes['analytics']}:user:{user_id}*"
            ]
            
            success = True
            for pattern in patterns:
                result = await self.cache_manager.delete_pattern(pattern)
                success = success and result
            
            logger.info("Invalidated user cache", user_id=user_id, success=success)
            return success
            
        except Exception as e:
            logger.error("Failed to invalidate user cache", user_id=user_id, error=str(e))
            return False
    
    async def invalidate_module_cache(self, module_id: str, tenant_id: str) -> bool:
        """Invalidate cache entries for a specific module."""
        try:
            patterns = [
                f"{self.prefixes['module']}:detail:{module_id}:{tenant_id}",
                f"{self.prefixes['module']}:list:{tenant_id}*",  # List caches might include this module
                f"{self.prefixes['search']}:*",  # Search results might include this module
                f"{self.prefixes['recommendations']}:*"  # Recommendations might be affected
            ]
            
            success = True
            for pattern in patterns:
                result = await self.cache_manager.delete_pattern(pattern)
                success = success and result
            
            logger.info("Invalidated module cache", module_id=module_id, success=success)
            return success
            
        except Exception as e:
            logger.error("Failed to invalidate module cache", module_id=module_id, error=str(e))
            return False
    
    async def warm_cache_for_user(self, user_id: str, tenant_id: str) -> bool:
        """Pre-warm cache with commonly accessed data for a user."""
        try:
            logger.info("Cache warming initiated", user_id=user_id, tenant_id=tenant_id)
            
            # Run cache warming tasks concurrently
            tasks = []
            
            # 1. Warm user enrollments cache
            tasks.append(self._warm_user_enrollments(user_id, tenant_id))
            
            # 2. Warm active modules cache for tenant
            tasks.append(self._warm_tenant_modules(tenant_id))
            
            # 3. Warm user progress data
            tasks.append(self._warm_user_progress(user_id, tenant_id))
            
            # 4. Warm recommendations cache
            tasks.append(self._warm_recommendations(user_id, tenant_id))
            
            # 5. Warm user certificates cache
            tasks.append(self._warm_user_certificates(user_id, tenant_id))
            
            # Execute all warming tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successful operations
            successful = sum(1 for r in results if r is True)
            total = len(results)
            
            logger.info(
                "Cache warming completed",
                user_id=user_id,
                tenant_id=tenant_id,
                successful=successful,
                total=total
            )
            
            # Consider warming successful if at least 80% of tasks succeeded
            return successful >= (total * 0.8)
            
        except Exception as e:
            logger.error("Failed to warm cache", user_id=user_id, error=str(e))
            return False
    
    async def _warm_user_enrollments(self, user_id: str, tenant_id: str) -> bool:
        """Warm cache with user's enrollment data."""
        try:
            # Simulate fetching enrollments from database
            from core_infra.database.connection import get_database
            
            async with get_database() as db:
                enrollments = await db.fetch_all(
                    """
                    SELECT e.*, m.title, m.description, m.difficulty_level
                    FROM training_enrollments e
                    JOIN training_modules m ON e.module_id = m.id
                    WHERE e.user_id = $1 AND e.tenant_id = $2
                    AND e.status IN ('active', 'in_progress')
                    ORDER BY e.enrolled_at DESC
                    """,
                    user_id, tenant_id
                )
                
                # Cache the results
                cache_key = self._build_cache_key('enrollment', 'user', user_id)
                await self.cache_manager.set(
                    cache_key,
                    [dict(e) for e in enrollments],
                    ttl=self.default_ttl
                )
                
                logger.debug("Warmed user enrollments cache", user_id=user_id, count=len(enrollments))
                return True
                
        except Exception as e:
            logger.error("Failed to warm user enrollments", user_id=user_id, error=str(e))
            return False
    
    async def _warm_tenant_modules(self, tenant_id: str) -> bool:
        """Warm cache with tenant's active modules."""
        try:
            from core_infra.database.connection import get_database
            
            async with get_database() as db:
                modules = await db.fetch_all(
                    """
                    SELECT * FROM training_modules
                    WHERE tenant_id = $1 AND is_active = true
                    ORDER BY created_at DESC
                    LIMIT 50
                    """,
                    tenant_id
                )
                
                # Cache the results
                cache_key = self._build_cache_key('module', 'tenant', tenant_id, 'active')
                await self.cache_manager.set(
                    cache_key,
                    [dict(m) for m in modules],
                    ttl=self.long_ttl
                )
                
                logger.debug("Warmed tenant modules cache", tenant_id=tenant_id, count=len(modules))
                return True
                
        except Exception as e:
            logger.error("Failed to warm tenant modules", tenant_id=tenant_id, error=str(e))
            return False
    
    async def _warm_user_progress(self, user_id: str, tenant_id: str) -> bool:
        """Warm cache with user's progress data."""
        try:
            from core_infra.database.connection import get_database
            
            async with get_database() as db:
                # Get active enrollments first
                enrollments = await db.fetch_all(
                    """
                    SELECT id FROM training_enrollments
                    WHERE user_id = $1 AND tenant_id = $2
                    AND status IN ('active', 'in_progress')
                    """,
                    user_id, tenant_id
                )
                
                # For each enrollment, cache progress
                for enrollment in enrollments:
                    progress = await db.fetch_one(
                        """
                        SELECT * FROM training_progress
                        WHERE enrollment_id = $1
                        ORDER BY last_accessed DESC
                        LIMIT 1
                        """,
                        enrollment['id']
                    )
                    
                    if progress:
                        cache_key = self._build_cache_key('progress', 'enrollment', str(enrollment['id']))
                        await self.cache_manager.set(
                            cache_key,
                            dict(progress),
                            ttl=self.default_ttl
                        )
                
                logger.debug("Warmed user progress cache", user_id=user_id, enrollments=len(enrollments))
                return True
                
        except Exception as e:
            logger.error("Failed to warm user progress", user_id=user_id, error=str(e))
            return False
    
    async def _warm_recommendations(self, user_id: str, tenant_id: str) -> bool:
        """Warm cache with personalized recommendations."""
        try:
            # Generate recommendations based on user's history
            recommendations = await self._generate_recommendations(user_id, tenant_id)
            
            # Cache the results
            cache_key = self._build_cache_key('recommendations', 'user', user_id)
            await self.cache_manager.set(
                cache_key,
                recommendations,
                ttl=self.default_ttl
            )
            
            logger.debug("Warmed recommendations cache", user_id=user_id, count=len(recommendations))
            return True
            
        except Exception as e:
            logger.error("Failed to warm recommendations", user_id=user_id, error=str(e))
            return False
    
    async def _warm_user_certificates(self, user_id: str, tenant_id: str) -> bool:
        """Warm cache with user's certificates."""
        try:
            from core_infra.database.connection import get_database
            
            async with get_database() as db:
                certificates = await db.fetch_all(
                    """
                    SELECT c.*, m.title as module_title
                    FROM training_certificates c
                    JOIN training_modules m ON c.module_id = m.id
                    WHERE c.user_id = $1 AND c.tenant_id = $2
                    ORDER BY c.issued_at DESC
                    """,
                    user_id, tenant_id
                )
                
                # Cache the results
                cache_key = self._build_cache_key('certificates', 'user', user_id)
                await self.cache_manager.set(
                    cache_key,
                    [dict(c) for c in certificates],
                    ttl=self.long_ttl
                )
                
                logger.debug("Warmed user certificates cache", user_id=user_id, count=len(certificates))
                return True
                
        except Exception as e:
            logger.error("Failed to warm user certificates", user_id=user_id, error=str(e))
            return False
    
    async def _generate_recommendations(self, user_id: str, tenant_id: str) -> List[Dict[str, Any]]:
        """Generate personalized module recommendations."""
        from core_infra.database.connection import get_database
        
        async with get_database() as db:
            # Get user's completed modules
            completed = await db.fetch_all(
                """
                SELECT DISTINCT module_id, m.category
                FROM training_enrollments e
                JOIN training_modules m ON e.module_id = m.id
                WHERE e.user_id = $1 AND e.status = 'completed'
                """,
                user_id
            )
            
            completed_ids = [c['module_id'] for c in completed]
            completed_categories = [c['category'] for c in completed]
            
            # Find recommended modules
            recommendations = await db.fetch_all(
                """
                SELECT m.*, AVG(e.rating) as avg_rating
                FROM training_modules m
                LEFT JOIN training_enrollments e ON m.id = e.module_id
                WHERE m.tenant_id = $1 
                AND m.is_active = true
                AND m.id NOT IN (SELECT unnest($2::uuid[]))
                AND (m.category = ANY($3::text[]) OR m.difficulty_level = 'beginner')
                GROUP BY m.id
                ORDER BY avg_rating DESC NULLS LAST, m.created_at DESC
                LIMIT 10
                """,
                tenant_id,
                completed_ids or [None],
                completed_categories or ['general']
            )
            
            return [dict(r) for r in recommendations]
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        try:
            stats = await self.cache_manager.get_stats()
            
            # Add training-specific metrics
            training_stats = {
                'cache_prefixes': list(self.prefixes.keys()),
                'default_ttl': self.default_ttl,
                'short_ttl': self.short_ttl,
                'long_ttl': self.long_ttl,
                **stats
            }
            
            return training_stats
            
        except Exception as e:
            logger.error("Failed to get cache stats", error=str(e))
            return {}


def cache_training_data(
    cache_key_func: callable = None,
    ttl: int = None,
    cache_service: TrainingCacheService = None
):
    """Decorator for caching training portal data."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get cache service instance
            cache_svc = cache_service or TrainingCacheService()
            
            # Build cache key
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
            else:
                cache_key = f"training:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            try:
                cached_result = await cache_svc.cache_manager.get(cache_key)
                if cached_result:
                    logger.debug("Cache hit", function=func.__name__, cache_key=cache_key)
                    return json.loads(cached_result)
            except Exception as e:
                logger.warning("Cache get failed", error=str(e))
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache the result
            try:
                await cache_svc.cache_manager.set(
                    cache_key,
                    json.dumps(result, default=str),
                    ttl or cache_svc.default_ttl
                )
                logger.debug("Cached result", function=func.__name__, cache_key=cache_key)
            except Exception as e:
                logger.warning("Cache set failed", error=str(e))
            
            return result
        return wrapper
    return decorator


# Global cache service instance
training_cache_service = TrainingCacheService()
