"""
Query Performance Optimizer for RegulensAI.
Implements intelligent query optimization, monitoring, and caching strategies.
"""

import asyncio
import time
import hashlib
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from functools import wraps
import structlog
from core_infra.caching.redis_cache_manager import get_cache_manager
from core_infra.database.connection_pool_manager import get_connection_pool_manager

logger = structlog.get_logger(__name__)


@dataclass
class QueryMetrics:
    """Query performance metrics."""
    query_hash: str
    query_text: str
    execution_count: int = 0
    total_execution_time: float = 0.0
    average_execution_time: float = 0.0
    min_execution_time: float = float('inf')
    max_execution_time: float = 0.0
    last_executed: Optional[datetime] = None
    cache_hits: int = 0
    cache_misses: int = 0
    error_count: int = 0
    optimization_applied: bool = False


@dataclass
class QueryOptimizationRule:
    """Query optimization rule."""
    name: str
    pattern: str
    replacement: str
    description: str
    enabled: bool = True


class QueryOptimizer:
    """
    Intelligent query optimizer with performance monitoring and caching.
    """
    
    def __init__(self, enable_caching: bool = True, enable_monitoring: bool = True):
        self.enable_caching = enable_caching
        self.enable_monitoring = enable_monitoring
        
        # Query metrics storage
        self.query_metrics: Dict[str, QueryMetrics] = {}
        
        # Optimization rules
        self.optimization_rules = self._initialize_optimization_rules()
        
        # Performance thresholds
        self.slow_query_threshold = 1.0  # seconds
        self.cache_ttl_default = 300  # 5 minutes
        
        # Get cache manager
        self.cache_manager = get_cache_manager()
        self.pool_manager = get_connection_pool_manager()
    
    def _initialize_optimization_rules(self) -> List[QueryOptimizationRule]:
        """Initialize query optimization rules."""
        return [
            QueryOptimizationRule(
                name="add_limit_to_unbounded_select",
                pattern=r"SELECT\s+.*\s+FROM\s+\w+(?:\s+WHERE\s+.*)?(?:\s+ORDER\s+BY\s+.*)?$",
                replacement=r"\g<0> LIMIT 1000",
                description="Add LIMIT to unbounded SELECT queries"
            ),
            QueryOptimizationRule(
                name="optimize_count_queries",
                pattern=r"SELECT\s+COUNT\(\*\)\s+FROM\s+(\w+)(?:\s+WHERE\s+(.*))?",
                replacement=r"SELECT COUNT(*) FROM \1 \2",
                description="Optimize COUNT(*) queries with better indexing hints"
            ),
            QueryOptimizationRule(
                name="add_index_hints",
                pattern=r"SELECT\s+.*\s+FROM\s+notifications\s+WHERE\s+tenant_id\s*=",
                replacement=r"\g<0> /*+ INDEX(notifications idx_notifications_tenant_date) */",
                description="Add index hints for tenant-based queries"
            ),
            QueryOptimizationRule(
                name="optimize_like_queries",
                pattern=r"WHERE\s+(\w+)\s+LIKE\s+'%(.*)%'",
                replacement=r"WHERE \1 ILIKE '%\2%'",
                description="Use ILIKE for case-insensitive pattern matching"
            ),
            QueryOptimizationRule(
                name="optimize_date_range_queries",
                pattern=r"WHERE\s+(\w+)\s+>=\s+'([^']+)'\s+AND\s+\1\s+<=\s+'([^']+)'",
                replacement=r"WHERE \1 BETWEEN '\2' AND '\3'",
                description="Use BETWEEN for date range queries"
            )
        ]
    
    def optimize_query(self, query: str) -> Tuple[str, List[str]]:
        """
        Apply optimization rules to a query.
        Returns optimized query and list of applied optimizations.
        """
        optimized_query = query.strip()
        applied_optimizations = []
        
        for rule in self.optimization_rules:
            if not rule.enabled:
                continue
            
            if re.search(rule.pattern, optimized_query, re.IGNORECASE):
                old_query = optimized_query
                optimized_query = re.sub(rule.pattern, rule.replacement, optimized_query, flags=re.IGNORECASE)
                
                if old_query != optimized_query:
                    applied_optimizations.append(rule.name)
                    logger.debug(f"Applied optimization rule: {rule.name}")
        
        return optimized_query, applied_optimizations
    
    def generate_query_hash(self, query: str, params: Optional[tuple] = None) -> str:
        """Generate hash for query caching."""
        # Normalize query for consistent hashing
        normalized_query = re.sub(r'\s+', ' ', query.strip().upper())
        
        # Include parameters in hash
        params_str = str(params) if params else ""
        
        # Generate hash
        hash_input = f"{normalized_query}:{params_str}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    def should_cache_query(self, query: str) -> bool:
        """Determine if a query should be cached."""
        # Don't cache write operations
        write_operations = ['INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER']
        query_upper = query.strip().upper()
        
        if any(query_upper.startswith(op) for op in write_operations):
            return False
        
        # Don't cache queries with NOW(), CURRENT_TIMESTAMP, etc.
        time_functions = ['NOW()', 'CURRENT_TIMESTAMP', 'CURRENT_DATE', 'CURRENT_TIME']
        if any(func in query_upper for func in time_functions):
            return False
        
        # Cache SELECT queries
        return query_upper.startswith('SELECT')
    
    def calculate_cache_ttl(self, query: str) -> int:
        """Calculate appropriate cache TTL based on query characteristics."""
        query_upper = query.upper()
        
        # Long TTL for reference data
        if any(table in query_upper for table in ['FEATURE_FLAGS', 'TENANT_CONFIGURATIONS', 'NOTIFICATION_TEMPLATES']):
            return 1800  # 30 minutes
        
        # Medium TTL for user data
        if any(table in query_upper for table in ['USERS', 'TENANT_USERS', 'USER_SESSIONS']):
            return 600   # 10 minutes
        
        # Short TTL for transactional data
        if any(table in query_upper for table in ['NOTIFICATIONS', 'ENTITY_SCREENINGS', 'AUDIT_LOGS']):
            return 300   # 5 minutes
        
        # Very short TTL for real-time data
        if any(table in query_upper for table in ['API_REQUEST_METRICS', 'SYSTEM_METRICS']):
            return 60    # 1 minute
        
        return self.cache_ttl_default
    
    async def execute_optimized_query(
        self,
        query: str,
        params: Optional[tuple] = None,
        fetch_mode: str = "all",
        force_refresh: bool = False
    ) -> Any:
        """
        Execute query with optimization, caching, and monitoring.
        """
        start_time = time.time()
        query_hash = self.generate_query_hash(query, params)
        
        try:
            # Apply query optimizations
            optimized_query, optimizations = self.optimize_query(query)
            
            # Check cache first (if enabled and appropriate)
            if (self.enable_caching and 
                self.cache_manager and 
                self.should_cache_query(optimized_query) and 
                not force_refresh):
                
                cached_result = await self.cache_manager.get(query_hash, "database_query")
                if cached_result is not None:
                    self._update_metrics(query_hash, query, time.time() - start_time, True, False)
                    return cached_result
            
            # Execute query
            if not self.pool_manager:
                raise RuntimeError("Connection pool manager not initialized")
            
            result = await self.pool_manager.execute_async_query(
                optimized_query, params, fetch_mode
            )
            
            # Cache result if appropriate
            if (self.enable_caching and 
                self.cache_manager and 
                self.should_cache_query(optimized_query)):
                
                cache_ttl = self.calculate_cache_ttl(optimized_query)
                await self.cache_manager.set(query_hash, result, "database_query", cache_ttl)
            
            # Update metrics
            execution_time = time.time() - start_time
            self._update_metrics(query_hash, query, execution_time, False, len(optimizations) > 0)
            
            # Log slow queries
            if execution_time > self.slow_query_threshold:
                logger.warning(f"Slow query detected: {execution_time:.2f}s - {query[:100]}...")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_metrics(query_hash, query, execution_time, False, False, error=True)
            logger.error(f"Query execution error: {e}")
            raise
    
    def _update_metrics(
        self,
        query_hash: str,
        query: str,
        execution_time: float,
        cache_hit: bool,
        optimization_applied: bool,
        error: bool = False
    ):
        """Update query performance metrics."""
        if not self.enable_monitoring:
            return
        
        if query_hash not in self.query_metrics:
            self.query_metrics[query_hash] = QueryMetrics(
                query_hash=query_hash,
                query_text=query[:200] + "..." if len(query) > 200 else query
            )
        
        metrics = self.query_metrics[query_hash]
        
        if error:
            metrics.error_count += 1
        else:
            metrics.execution_count += 1
            metrics.total_execution_time += execution_time
            metrics.average_execution_time = metrics.total_execution_time / metrics.execution_count
            metrics.min_execution_time = min(metrics.min_execution_time, execution_time)
            metrics.max_execution_time = max(metrics.max_execution_time, execution_time)
            
            if cache_hit:
                metrics.cache_hits += 1
            else:
                metrics.cache_misses += 1
        
        metrics.last_executed = datetime.utcnow()
        metrics.optimization_applied = optimization_applied
    
    def get_query_metrics(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get query performance metrics."""
        # Sort by average execution time (slowest first)
        sorted_metrics = sorted(
            self.query_metrics.values(),
            key=lambda m: m.average_execution_time,
            reverse=True
        )
        
        return [asdict(metric) for metric in sorted_metrics[:limit]]
    
    def get_slow_queries(self, threshold: float = None) -> List[Dict[str, Any]]:
        """Get queries that exceed the slow query threshold."""
        threshold = threshold or self.slow_query_threshold
        
        slow_queries = [
            asdict(metric) for metric in self.query_metrics.values()
            if metric.average_execution_time > threshold
        ]
        
        return sorted(slow_queries, key=lambda q: q['average_execution_time'], reverse=True)
    
    def get_cache_performance(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_hits = sum(m.cache_hits for m in self.query_metrics.values())
        total_misses = sum(m.cache_misses for m in self.query_metrics.values())
        total_requests = total_hits + total_misses
        
        return {
            "total_cache_hits": total_hits,
            "total_cache_misses": total_misses,
            "total_requests": total_requests,
            "cache_hit_ratio": total_hits / total_requests if total_requests > 0 else 0.0,
            "queries_using_cache": len([m for m in self.query_metrics.values() if m.cache_hits > 0])
        }
    
    def analyze_query_patterns(self) -> Dict[str, Any]:
        """Analyze query patterns for optimization opportunities."""
        analysis = {
            "total_queries": len(self.query_metrics),
            "total_executions": sum(m.execution_count for m in self.query_metrics.values()),
            "average_execution_time": 0.0,
            "slow_query_count": 0,
            "most_frequent_queries": [],
            "optimization_opportunities": []
        }
        
        if not self.query_metrics:
            return analysis
        
        # Calculate overall average execution time
        total_time = sum(m.total_execution_time for m in self.query_metrics.values())
        total_executions = sum(m.execution_count for m in self.query_metrics.values())
        analysis["average_execution_time"] = total_time / total_executions if total_executions > 0 else 0.0
        
        # Count slow queries
        analysis["slow_query_count"] = len([
            m for m in self.query_metrics.values()
            if m.average_execution_time > self.slow_query_threshold
        ])
        
        # Most frequent queries
        frequent_queries = sorted(
            self.query_metrics.values(),
            key=lambda m: m.execution_count,
            reverse=True
        )[:10]
        
        analysis["most_frequent_queries"] = [
            {
                "query_hash": m.query_hash,
                "query_text": m.query_text,
                "execution_count": m.execution_count,
                "average_execution_time": m.average_execution_time
            }
            for m in frequent_queries
        ]
        
        # Optimization opportunities
        opportunities = []
        
        # Queries without optimization
        unoptimized_slow = [
            m for m in self.query_metrics.values()
            if not m.optimization_applied and m.average_execution_time > self.slow_query_threshold
        ]
        
        if unoptimized_slow:
            opportunities.append({
                "type": "unoptimized_slow_queries",
                "count": len(unoptimized_slow),
                "description": "Slow queries that could benefit from optimization rules"
            })
        
        # Queries with low cache hit ratio
        low_cache_hit = [
            m for m in self.query_metrics.values()
            if m.cache_hits + m.cache_misses > 10 and 
            m.cache_hits / (m.cache_hits + m.cache_misses) < 0.5
        ]
        
        if low_cache_hit:
            opportunities.append({
                "type": "low_cache_hit_ratio",
                "count": len(low_cache_hit),
                "description": "Queries with low cache hit ratio that might need TTL adjustment"
            })
        
        analysis["optimization_opportunities"] = opportunities
        
        return analysis
    
    def clear_metrics(self):
        """Clear all query metrics."""
        self.query_metrics.clear()
        logger.info("Query metrics cleared")
    
    def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics for external analysis."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "query_metrics": [asdict(metric) for metric in self.query_metrics.values()],
            "cache_performance": self.get_cache_performance(),
            "analysis": self.analyze_query_patterns(),
            "configuration": {
                "slow_query_threshold": self.slow_query_threshold,
                "cache_ttl_default": self.cache_ttl_default,
                "enable_caching": self.enable_caching,
                "enable_monitoring": self.enable_monitoring
            }
        }


# Decorator for automatic query optimization
def optimized_query(
    fetch_mode: str = "all",
    cache_ttl: Optional[int] = None,
    force_refresh: bool = False
):
    """Decorator to automatically optimize and cache query results."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract query and params from function
            if 'query' in kwargs:
                query = kwargs['query']
                params = kwargs.get('params')
            elif len(args) >= 1:
                query = args[0]
                params = args[1] if len(args) >= 2 else None
            else:
                # If no query found, execute function normally
                return await func(*args, **kwargs)
            
            # Use query optimizer
            optimizer = get_query_optimizer()
            if optimizer:
                return await optimizer.execute_optimized_query(
                    query, params, fetch_mode, force_refresh
                )
            else:
                # Fallback to normal execution
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# Global query optimizer instance
_query_optimizer: Optional[QueryOptimizer] = None


def initialize_query_optimizer(
    enable_caching: bool = True,
    enable_monitoring: bool = True
) -> QueryOptimizer:
    """Initialize global query optimizer."""
    global _query_optimizer
    
    _query_optimizer = QueryOptimizer(enable_caching, enable_monitoring)
    logger.info("Query optimizer initialized")
    
    return _query_optimizer


def get_query_optimizer() -> Optional[QueryOptimizer]:
    """Get the global query optimizer instance."""
    return _query_optimizer
