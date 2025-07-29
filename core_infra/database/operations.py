"""
Regulens AI - Database Operations Framework
Enterprise-grade database operations with connection pooling, health monitoring, and optimization.
"""

import asyncio
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from contextlib import asynccontextmanager
import asyncpg
import structlog

from core_infra.config import get_settings
from core_infra.database.connection import get_database
from core_infra.exceptions import DatabaseException, SystemException

# Initialize logging
logger = structlog.get_logger(__name__)
settings = get_settings()

class DatabaseOperations:
    """Comprehensive database operations and management."""
    
    def __init__(self):
        self.connection_pool = None
        self.health_check_interval = 60  # seconds
        self.performance_metrics = {}
        
    async def initialize(self):
        """Initialize database operations."""
        try:
            await self._setup_connection_pool()
            await self._verify_schema()
            await self._setup_monitoring()
            logger.info("Database operations initialized successfully")
        except Exception as e:
            logger.error(f"Database operations initialization failed: {e}")
            raise SystemException(f"Database initialization failed: {e}")
    
    async def _setup_connection_pool(self):
        """Setup optimized connection pool."""
        try:
            database_url = settings.database_url
            
            self.connection_pool = await asyncpg.create_pool(
                database_url,
                min_size=5,
                max_size=20,
                max_queries=50000,
                max_inactive_connection_lifetime=300,
                command_timeout=60,
                server_settings={
                    'application_name': 'regulens_ai',
                    'timezone': 'UTC'
                }
            )
            
            logger.info("Database connection pool created successfully")
            
        except Exception as e:
            logger.error(f"Connection pool setup failed: {e}")
            raise DatabaseException("connection_pool", str(e))
    
    async def _verify_schema(self):
        """Verify database schema integrity."""
        try:
            async with self.connection_pool.acquire() as conn:
                # Check critical tables exist
                critical_tables = [
                    'tenants', 'users', 'user_credentials', 'permissions',
                    'customers', 'transactions', 'alerts', 'notifications',
                    'compliance_programs', 'compliance_requirements'
                ]
                
                for table in critical_tables:
                    result = await conn.fetchval(
                        """
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = $1
                        )
                        """,
                        table
                    )
                    
                    if not result:
                        raise DatabaseException("schema_verification", f"Missing critical table: {table}")
                
                logger.info("Database schema verification completed successfully")
                
        except Exception as e:
            logger.error(f"Schema verification failed: {e}")
            raise DatabaseException("schema_verification", str(e))
    
    async def _setup_monitoring(self):
        """Setup database monitoring and health checks."""
        try:
            # Start background health check task
            asyncio.create_task(self._health_check_loop())
            logger.info("Database monitoring setup completed")
        except Exception as e:
            logger.error(f"Monitoring setup failed: {e}")
    
    async def _health_check_loop(self):
        """Background health check loop."""
        while True:
            try:
                await self.perform_health_check()
                await asyncio.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(30)  # Shorter interval on error
    
    async def perform_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive database health check."""
        health_status = {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'healthy',
            'checks': {}
        }
        
        try:
            start_time = time.time()
            
            async with self.connection_pool.acquire() as conn:
                # Connection test
                await conn.fetchval('SELECT 1')
                connection_time = (time.time() - start_time) * 1000
                
                health_status['checks']['connection'] = {
                    'status': 'healthy',
                    'response_time_ms': round(connection_time, 2)
                }
                
                # Pool status
                pool_status = await self._check_pool_status()
                health_status['checks']['connection_pool'] = pool_status
                
                # Database size check
                db_size = await self._check_database_size(conn)
                health_status['checks']['database_size'] = db_size
                
                # Active connections
                active_connections = await self._check_active_connections(conn)
                health_status['checks']['active_connections'] = active_connections
                
                # Long running queries
                long_queries = await self._check_long_running_queries(conn)
                health_status['checks']['long_running_queries'] = long_queries
                
                # Table statistics
                table_stats = await self._check_table_statistics(conn)
                health_status['checks']['table_statistics'] = table_stats
                
            # Store health check result
            await self._store_health_check(health_status)
            
            # Determine overall status
            failed_checks = [
                check for check in health_status['checks'].values()
                if check.get('status') != 'healthy'
            ]
            
            if failed_checks:
                health_status['overall_status'] = 'degraded' if len(failed_checks) < 3 else 'unhealthy'
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            health_status['overall_status'] = 'unhealthy'
            health_status['error'] = str(e)
            return health_status
    
    async def _check_pool_status(self) -> Dict[str, Any]:
        """Check connection pool status."""
        try:
            pool = self.connection_pool
            return {
                'status': 'healthy',
                'size': pool.get_size(),
                'min_size': pool.get_min_size(),
                'max_size': pool.get_max_size(),
                'idle_connections': pool.get_idle_size()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    async def _check_database_size(self, conn) -> Dict[str, Any]:
        """Check database size and growth."""
        try:
            size_query = """
                SELECT 
                    pg_size_pretty(pg_database_size(current_database())) as size,
                    pg_database_size(current_database()) as size_bytes
            """
            result = await conn.fetchrow(size_query)
            
            return {
                'status': 'healthy',
                'size': result['size'],
                'size_bytes': result['size_bytes']
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    async def _check_active_connections(self, conn) -> Dict[str, Any]:
        """Check active database connections."""
        try:
            connections_query = """
                SELECT 
                    count(*) as total_connections,
                    count(*) FILTER (WHERE state = 'active') as active_connections,
                    count(*) FILTER (WHERE state = 'idle') as idle_connections
                FROM pg_stat_activity 
                WHERE datname = current_database()
            """
            result = await conn.fetchrow(connections_query)
            
            status = 'healthy'
            if result['total_connections'] > 80:  # Warning threshold
                status = 'warning'
            if result['total_connections'] > 95:  # Critical threshold
                status = 'critical'
            
            return {
                'status': status,
                'total_connections': result['total_connections'],
                'active_connections': result['active_connections'],
                'idle_connections': result['idle_connections']
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    async def _check_long_running_queries(self, conn) -> Dict[str, Any]:
        """Check for long-running queries."""
        try:
            long_queries_query = """
                SELECT 
                    count(*) as long_running_count,
                    max(extract(epoch from (now() - query_start))) as max_duration_seconds
                FROM pg_stat_activity 
                WHERE datname = current_database()
                AND state = 'active'
                AND query_start < now() - interval '5 minutes'
                AND query NOT LIKE '%pg_stat_activity%'
            """
            result = await conn.fetchrow(long_queries_query)
            
            status = 'healthy'
            if result['long_running_count'] > 0:
                status = 'warning'
            if result['long_running_count'] > 5:
                status = 'critical'
            
            return {
                'status': status,
                'long_running_count': result['long_running_count'],
                'max_duration_seconds': result['max_duration_seconds']
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    async def _check_table_statistics(self, conn) -> Dict[str, Any]:
        """Check table statistics and sizes."""
        try:
            table_stats_query = """
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes
                FROM pg_stat_user_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 10
            """
            results = await conn.fetch(table_stats_query)
            
            tables = []
            for row in results:
                tables.append({
                    'table_name': row['tablename'],
                    'size': row['size'],
                    'size_bytes': row['size_bytes'],
                    'inserts': row['inserts'],
                    'updates': row['updates'],
                    'deletes': row['deletes']
                })
            
            return {
                'status': 'healthy',
                'largest_tables': tables
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    async def _store_health_check(self, health_status: Dict[str, Any]):
        """Store health check results."""
        try:
            async with get_database() as db:
                await db.execute(
                    """
                    INSERT INTO system_health_checks (
                        service_name, check_type, status, response_time_ms, metadata
                    ) VALUES ($1, $2, $3, $4, $5)
                    """,
                    'database',
                    'comprehensive',
                    health_status['overall_status'],
                    health_status['checks'].get('connection', {}).get('response_time_ms'),
                    health_status
                )
        except Exception as e:
            logger.error(f"Failed to store health check: {e}")
    
    async def optimize_database(self) -> Dict[str, Any]:
        """Perform database optimization operations."""
        optimization_results = {
            'timestamp': datetime.utcnow().isoformat(),
            'operations': {}
        }
        
        try:
            async with self.connection_pool.acquire() as conn:
                # Analyze tables for query optimization
                await self._analyze_tables(conn, optimization_results)
                
                # Vacuum operations
                await self._vacuum_operations(conn, optimization_results)
                
                # Index maintenance
                await self._index_maintenance(conn, optimization_results)
                
                # Update statistics
                await self._update_statistics(conn, optimization_results)
                
            logger.info("Database optimization completed successfully")
            return optimization_results
            
        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
            optimization_results['error'] = str(e)
            return optimization_results
    
    async def _analyze_tables(self, conn, results: Dict[str, Any]):
        """Analyze tables for query optimization."""
        try:
            # Get list of tables to analyze
            tables_query = """
                SELECT tablename 
                FROM pg_stat_user_tables 
                WHERE schemaname = 'public'
                ORDER BY n_tup_ins + n_tup_upd + n_tup_del DESC
                LIMIT 20
            """
            tables = await conn.fetch(tables_query)
            
            analyzed_tables = []
            for table in tables:
                table_name = table['tablename']
                try:
                    await conn.execute(f'ANALYZE public.{table_name}')
                    analyzed_tables.append(table_name)
                except Exception as e:
                    logger.warning(f"Failed to analyze table {table_name}: {e}")
            
            results['operations']['analyze_tables'] = {
                'status': 'completed',
                'tables_analyzed': analyzed_tables,
                'count': len(analyzed_tables)
            }
            
        except Exception as e:
            results['operations']['analyze_tables'] = {
                'status': 'failed',
                'error': str(e)
            }
    
    async def _vacuum_operations(self, conn, results: Dict[str, Any]):
        """Perform vacuum operations."""
        try:
            # Vacuum analyze on high-activity tables
            high_activity_tables = [
                'audit_logs', 'performance_metrics', 'system_health_checks',
                'user_sessions', 'notifications', 'alerts'
            ]
            
            vacuumed_tables = []
            for table in high_activity_tables:
                try:
                    await conn.execute(f'VACUUM ANALYZE public.{table}')
                    vacuumed_tables.append(table)
                except Exception as e:
                    logger.warning(f"Failed to vacuum table {table}: {e}")
            
            results['operations']['vacuum'] = {
                'status': 'completed',
                'tables_vacuumed': vacuumed_tables,
                'count': len(vacuumed_tables)
            }
            
        except Exception as e:
            results['operations']['vacuum'] = {
                'status': 'failed',
                'error': str(e)
            }
    
    async def _index_maintenance(self, conn, results: Dict[str, Any]):
        """Perform index maintenance."""
        try:
            # Check for unused indexes
            unused_indexes_query = """
                SELECT 
                    schemaname, tablename, indexname, idx_scan
                FROM pg_stat_user_indexes 
                WHERE schemaname = 'public'
                AND idx_scan = 0
                AND indexname NOT LIKE '%_pkey'
            """
            unused_indexes = await conn.fetch(unused_indexes_query)
            
            # Check for missing indexes (tables with high seq_scan)
            missing_indexes_query = """
                SELECT 
                    schemaname, tablename, seq_scan, seq_tup_read,
                    seq_tup_read / GREATEST(seq_scan, 1) as avg_tup_per_scan
                FROM pg_stat_user_tables 
                WHERE schemaname = 'public'
                AND seq_scan > 1000
                AND seq_tup_read / GREATEST(seq_scan, 1) > 10000
                ORDER BY seq_tup_read DESC
            """
            potential_missing_indexes = await conn.fetch(missing_indexes_query)
            
            results['operations']['index_maintenance'] = {
                'status': 'completed',
                'unused_indexes': [dict(idx) for idx in unused_indexes],
                'potential_missing_indexes': [dict(idx) for idx in potential_missing_indexes]
            }
            
        except Exception as e:
            results['operations']['index_maintenance'] = {
                'status': 'failed',
                'error': str(e)
            }
    
    async def _update_statistics(self, conn, results: Dict[str, Any]):
        """Update database statistics."""
        try:
            # Update table statistics
            await conn.execute('ANALYZE')
            
            results['operations']['update_statistics'] = {
                'status': 'completed',
                'operation': 'full_analyze'
            }
            
        except Exception as e:
            results['operations']['update_statistics'] = {
                'status': 'failed',
                'error': str(e)
            }
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get database performance metrics."""
        try:
            async with self.connection_pool.acquire() as conn:
                metrics = {}
                
                # Query performance metrics
                query_stats = await conn.fetchrow("""
                    SELECT 
                        sum(calls) as total_calls,
                        sum(total_time) as total_time_ms,
                        avg(mean_time) as avg_time_ms,
                        max(max_time) as max_time_ms
                    FROM pg_stat_statements
                """)
                
                if query_stats:
                    metrics['query_performance'] = dict(query_stats)
                
                # Connection metrics
                conn_stats = await conn.fetchrow("""
                    SELECT 
                        count(*) as total_connections,
                        count(*) FILTER (WHERE state = 'active') as active_connections,
                        count(*) FILTER (WHERE state = 'idle') as idle_connections,
                        count(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction
                    FROM pg_stat_activity 
                    WHERE datname = current_database()
                """)
                
                metrics['connections'] = dict(conn_stats)
                
                # Database size metrics
                size_stats = await conn.fetchrow("""
                    SELECT 
                        pg_database_size(current_database()) as database_size_bytes,
                        pg_size_pretty(pg_database_size(current_database())) as database_size
                """)
                
                metrics['database_size'] = dict(size_stats)
                
                return metrics
                
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {'error': str(e)}
    
    async def cleanup_old_data(self, retention_days: int = 90) -> Dict[str, Any]:
        """Clean up old data based on retention policies."""
        cleanup_results = {
            'timestamp': datetime.utcnow().isoformat(),
            'retention_days': retention_days,
            'operations': {}
        }
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            async with get_database() as db:
                # Clean up old audit logs
                audit_deleted = await db.execute(
                    "DELETE FROM audit_logs WHERE created_at < $1",
                    cutoff_date
                )
                cleanup_results['operations']['audit_logs'] = {
                    'deleted_rows': int(audit_deleted.split()[-1])
                }
                
                # Clean up old performance metrics
                metrics_deleted = await db.execute(
                    "DELETE FROM performance_metrics WHERE timestamp < $1",
                    cutoff_date
                )
                cleanup_results['operations']['performance_metrics'] = {
                    'deleted_rows': int(metrics_deleted.split()[-1])
                }
                
                # Clean up old health checks
                health_deleted = await db.execute(
                    "DELETE FROM system_health_checks WHERE checked_at < $1",
                    cutoff_date
                )
                cleanup_results['operations']['health_checks'] = {
                    'deleted_rows': int(health_deleted.split()[-1])
                }
                
                # Clean up old user sessions
                sessions_deleted = await db.execute(
                    "DELETE FROM user_sessions WHERE expires_at < $1",
                    datetime.utcnow()
                )
                cleanup_results['operations']['expired_sessions'] = {
                    'deleted_rows': int(sessions_deleted.split()[-1])
                }
                
            logger.info(f"Data cleanup completed: {cleanup_results}")
            return cleanup_results
            
        except Exception as e:
            logger.error(f"Data cleanup failed: {e}")
            cleanup_results['error'] = str(e)
            return cleanup_results

# Global database operations instance
db_operations = DatabaseOperations()

# Convenience functions
async def perform_health_check() -> Dict[str, Any]:
    """Convenience function for health check."""
    return await db_operations.perform_health_check()

async def optimize_database() -> Dict[str, Any]:
    """Convenience function for database optimization."""
    return await db_operations.optimize_database()

async def get_performance_metrics() -> Dict[str, Any]:
    """Convenience function for performance metrics."""
    return await db_operations.get_performance_metrics()

async def cleanup_old_data(retention_days: int = 90) -> Dict[str, Any]:
    """Convenience function for data cleanup."""
    return await db_operations.cleanup_old_data(retention_days)
