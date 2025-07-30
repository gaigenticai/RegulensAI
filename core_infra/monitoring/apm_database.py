"""
APM-Enhanced Database Connection and Query Monitoring
Comprehensive database performance tracking with automatic query analysis and optimization recommendations.
"""

import asyncio
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from contextlib import asynccontextmanager
import asyncpg
import structlog

from core_infra.config import get_settings
from core_infra.logging.centralized_logging import get_centralized_logger, LogCategory
from core_infra.monitoring.apm_integration import apm_manager, track_database_operation


logger = structlog.get_logger(__name__)


class APMDatabaseConnection:
    """APM-enhanced database connection wrapper."""
    
    def __init__(self, connection: asyncpg.Connection):
        self.connection = connection
        self.settings = get_settings()
        self.query_cache = {}
        self.connection_stats = {
            'queries_executed': 0,
            'total_execution_time': 0.0,
            'slow_queries': 0,
            'failed_queries': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
    
    async def execute(self, query: str, *args, **kwargs) -> str:
        """Execute query with APM tracking."""
        return await self._execute_with_tracking('execute', query, *args, **kwargs)
    
    async def fetch(self, query: str, *args, **kwargs) -> List[asyncpg.Record]:
        """Fetch query results with APM tracking."""
        return await self._execute_with_tracking('fetch', query, *args, **kwargs)
    
    async def fetchrow(self, query: str, *args, **kwargs) -> Optional[asyncpg.Record]:
        """Fetch single row with APM tracking."""
        return await self._execute_with_tracking('fetchrow', query, *args, **kwargs)
    
    async def fetchval(self, query: str, *args, **kwargs) -> Any:
        """Fetch single value with APM tracking."""
        return await self._execute_with_tracking('fetchval', query, *args, **kwargs)
    
    async def executemany(self, query: str, args_list: List[Tuple], **kwargs) -> None:
        """Execute many queries with APM tracking."""
        return await self._execute_with_tracking('executemany', query, args_list, **kwargs)
    
    async def _execute_with_tracking(self, method: str, query: str, *args, **kwargs):
        """Execute database operation with comprehensive tracking."""
        start_time = time.time()
        query_hash = self._get_query_hash(query)
        normalized_query = self._normalize_query(query)
        error_occurred = None
        result = None
        
        # Update connection stats
        self.connection_stats['queries_executed'] += 1
        
        try:
            # Get the actual method from the connection
            db_method = getattr(self.connection, method)
            
            # Execute the query
            result = await db_method(query, *args, **kwargs)
            
            return result
            
        except Exception as e:
            error_occurred = e
            self.connection_stats['failed_queries'] += 1
            
            # Log database error
            apm_logger = await get_centralized_logger("apm_database")
            await apm_logger.error(
                f"Database query failed: {str(e)}",
                category=LogCategory.DATABASE,
                query_hash=query_hash,
                normalized_query=normalized_query,
                method=method,
                error_type=type(e).__name__,
                stack_trace=str(e)
            )
            
            raise
            
        finally:
            # Calculate execution time
            execution_time = time.time() - start_time
            self.connection_stats['total_execution_time'] += execution_time
            
            # Check for slow query
            if execution_time > self.settings.db_slow_query_threshold:
                self.connection_stats['slow_queries'] += 1
                
                # Log slow query
                apm_logger = await get_centralized_logger("apm_database")
                await apm_logger.warning(
                    f"Slow database query detected: {execution_time:.3f}s",
                    category=LogCategory.PERFORMANCE,
                    query_hash=query_hash,
                    normalized_query=normalized_query,
                    execution_time=execution_time,
                    threshold=self.settings.db_slow_query_threshold,
                    method=method,
                    args_count=len(args) if args else 0
                )
            
            # Track in APM system
            await track_database_operation(normalized_query, execution_time, error_occurred)
            
            # Store query performance data
            await self._store_query_performance(
                query_hash,
                normalized_query,
                method,
                execution_time,
                error_occurred,
                len(args) if args else 0
            )
    
    def _get_query_hash(self, query: str) -> str:
        """Generate hash for query identification."""
        normalized = self._normalize_query(query)
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
    
    def _normalize_query(self, query: str) -> str:
        """Normalize SQL query for analysis."""
        import re
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', query.strip())
        
        # Replace string literals
        normalized = re.sub(r"'[^']*'", "'?'", normalized)
        
        # Replace numeric literals
        normalized = re.sub(r'\b\d+\b', '?', normalized)
        
        # Replace parameter placeholders
        normalized = re.sub(r'\$\d+', '$?', normalized)
        
        # Replace IN clauses with multiple values
        normalized = re.sub(r'IN\s*\([^)]+\)', 'IN (?)', normalized, flags=re.IGNORECASE)
        
        return normalized.upper()
    
    async def _store_query_performance(
        self,
        query_hash: str,
        normalized_query: str,
        method: str,
        execution_time: float,
        error: Optional[Exception],
        args_count: int
    ):
        """Store query performance data for analysis."""
        performance_data = {
            'timestamp': datetime.utcnow(),
            'query_hash': query_hash,
            'normalized_query': normalized_query,
            'method': method,
            'execution_time': execution_time,
            'success': error is None,
            'error_type': type(error).__name__ if error else None,
            'args_count': args_count
        }
        
        # Store in query cache for analysis
        if query_hash not in self.query_cache:
            self.query_cache[query_hash] = {
                'normalized_query': normalized_query,
                'executions': [],
                'total_time': 0.0,
                'avg_time': 0.0,
                'min_time': float('inf'),
                'max_time': 0.0,
                'error_count': 0,
                'success_count': 0
            }
        
        cache_entry = self.query_cache[query_hash]
        cache_entry['executions'].append(performance_data)
        cache_entry['total_time'] += execution_time
        cache_entry['min_time'] = min(cache_entry['min_time'], execution_time)
        cache_entry['max_time'] = max(cache_entry['max_time'], execution_time)
        
        if error:
            cache_entry['error_count'] += 1
        else:
            cache_entry['success_count'] += 1
        
        total_executions = cache_entry['success_count'] + cache_entry['error_count']
        cache_entry['avg_time'] = cache_entry['total_time'] / total_executions
        
        # Keep only recent executions (last 100)
        if len(cache_entry['executions']) > 100:
            cache_entry['executions'] = cache_entry['executions'][-100:]
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection performance statistics."""
        avg_execution_time = (
            self.connection_stats['total_execution_time'] / self.connection_stats['queries_executed']
            if self.connection_stats['queries_executed'] > 0 else 0
        )
        
        return {
            **self.connection_stats,
            'avg_execution_time': avg_execution_time,
            'slow_query_percentage': (
                (self.connection_stats['slow_queries'] / self.connection_stats['queries_executed']) * 100
                if self.connection_stats['queries_executed'] > 0 else 0
            ),
            'error_rate': (
                (self.connection_stats['failed_queries'] / self.connection_stats['queries_executed']) * 100
                if self.connection_stats['queries_executed'] > 0 else 0
            )
        }
    
    def get_query_analysis(self) -> Dict[str, Any]:
        """Get detailed query performance analysis."""
        if not self.query_cache:
            return {}
        
        # Find slowest queries
        slowest_queries = sorted(
            self.query_cache.items(),
            key=lambda x: x[1]['avg_time'],
            reverse=True
        )[:10]
        
        # Find most frequent queries
        most_frequent = sorted(
            self.query_cache.items(),
            key=lambda x: len(x[1]['executions']),
            reverse=True
        )[:10]
        
        # Find queries with highest error rates
        highest_error_rate = sorted(
            self.query_cache.items(),
            key=lambda x: x[1]['error_count'] / (x[1]['success_count'] + x[1]['error_count']) if (x[1]['success_count'] + x[1]['error_count']) > 0 else 0,
            reverse=True
        )[:10]
        
        return {
            'total_unique_queries': len(self.query_cache),
            'slowest_queries': [
                {
                    'query_hash': query_hash,
                    'normalized_query': data['normalized_query'][:200] + '...' if len(data['normalized_query']) > 200 else data['normalized_query'],
                    'avg_time': data['avg_time'],
                    'max_time': data['max_time'],
                    'execution_count': len(data['executions'])
                }
                for query_hash, data in slowest_queries
            ],
            'most_frequent_queries': [
                {
                    'query_hash': query_hash,
                    'normalized_query': data['normalized_query'][:200] + '...' if len(data['normalized_query']) > 200 else data['normalized_query'],
                    'execution_count': len(data['executions']),
                    'avg_time': data['avg_time'],
                    'total_time': data['total_time']
                }
                for query_hash, data in most_frequent
            ],
            'highest_error_rate_queries': [
                {
                    'query_hash': query_hash,
                    'normalized_query': data['normalized_query'][:200] + '...' if len(data['normalized_query']) > 200 else data['normalized_query'],
                    'error_count': data['error_count'],
                    'success_count': data['success_count'],
                    'error_rate': (data['error_count'] / (data['success_count'] + data['error_count']) * 100) if (data['success_count'] + data['error_count']) > 0 else 0
                }
                for query_hash, data in highest_error_rate if data['error_count'] > 0
            ]
        }
    
    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Generate query optimization recommendations."""
        recommendations = []
        
        for query_hash, data in self.query_cache.items():
            if data['avg_time'] > self.settings.db_slow_query_threshold:
                recommendations.append({
                    'type': 'slow_query',
                    'priority': 'high',
                    'query_hash': query_hash,
                    'normalized_query': data['normalized_query'][:200] + '...' if len(data['normalized_query']) > 200 else data['normalized_query'],
                    'avg_time': data['avg_time'],
                    'execution_count': len(data['executions']),
                    'recommendation': 'Consider adding indexes, optimizing WHERE clauses, or breaking down complex queries'
                })
            
            if len(data['executions']) > 50 and data['avg_time'] > 0.1:  # Frequent and somewhat slow
                recommendations.append({
                    'type': 'frequent_slow_query',
                    'priority': 'medium',
                    'query_hash': query_hash,
                    'normalized_query': data['normalized_query'][:200] + '...' if len(data['normalized_query']) > 200 else data['normalized_query'],
                    'avg_time': data['avg_time'],
                    'execution_count': len(data['executions']),
                    'recommendation': 'Consider caching results or optimizing this frequently executed query'
                })
            
            error_rate = (data['error_count'] / (data['success_count'] + data['error_count']) * 100) if (data['success_count'] + data['error_count']) > 0 else 0
            if error_rate > 5:  # More than 5% error rate
                recommendations.append({
                    'type': 'high_error_rate',
                    'priority': 'high',
                    'query_hash': query_hash,
                    'normalized_query': data['normalized_query'][:200] + '...' if len(data['normalized_query']) > 200 else data['normalized_query'],
                    'error_rate': error_rate,
                    'error_count': data['error_count'],
                    'recommendation': 'Investigate query logic and data constraints causing frequent errors'
                })
        
        return sorted(recommendations, key=lambda x: {'high': 3, 'medium': 2, 'low': 1}[x['priority']], reverse=True)


class APMDatabasePool:
    """APM-enhanced database connection pool."""
    
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self.settings = get_settings()
        self.pool_stats = {
            'connections_created': 0,
            'connections_closed': 0,
            'active_connections': 0,
            'idle_connections': 0,
            'connection_errors': 0,
            'pool_exhausted_count': 0
        }
    
    @asynccontextmanager
    async def acquire(self):
        """Acquire connection from pool with APM tracking."""
        start_time = time.time()
        connection = None
        
        try:
            # Acquire connection from pool
            connection = await self.pool.acquire()
            self.pool_stats['active_connections'] += 1
            
            # Wrap connection with APM monitoring
            apm_connection = APMDatabaseConnection(connection)
            
            yield apm_connection
            
        except asyncpg.exceptions.TooManyConnectionsError:
            self.pool_stats['pool_exhausted_count'] += 1
            
            # Log pool exhaustion
            apm_logger = await get_centralized_logger("apm_database_pool")
            await apm_logger.critical(
                "Database connection pool exhausted",
                category=LogCategory.DATABASE,
                pool_size=self.pool.get_size(),
                active_connections=self.pool_stats['active_connections'],
                pool_stats=self.pool_stats
            )
            
            raise
            
        except Exception as e:
            self.pool_stats['connection_errors'] += 1
            
            # Log connection error
            apm_logger = await get_centralized_logger("apm_database_pool")
            await apm_logger.error(
                f"Database connection error: {str(e)}",
                category=LogCategory.DATABASE,
                error_type=type(e).__name__,
                pool_stats=self.pool_stats
            )
            
            raise
            
        finally:
            if connection:
                # Release connection back to pool
                await self.pool.release(connection)
                self.pool_stats['active_connections'] -= 1
                
                # Track connection usage time
                connection_time = time.time() - start_time
                
                # Track in APM
                await apm_manager.track_business_metric(
                    'database_connection_time',
                    connection_time,
                    pool_size=str(self.pool.get_size())
                )
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        return {
            **self.pool_stats,
            'pool_size': self.pool.get_size(),
            'pool_min_size': self.pool.get_min_size(),
            'pool_max_size': self.pool.get_max_size(),
            'current_pool_size': len(self.pool._holders) if hasattr(self.pool, '_holders') else 0
        }
