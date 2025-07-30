"""
Advanced Database Connection Pool Manager for RegulensAI.
Implements optimized connection pooling with monitoring and auto-scaling.
"""

import asyncio
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from contextlib import asynccontextmanager
import structlog
import asyncpg
import psycopg2
from psycopg2 import pool
from dataclasses import dataclass
import weakref

logger = structlog.get_logger(__name__)


@dataclass
class PoolConfig:
    """Database connection pool configuration."""
    min_connections: int = 5
    max_connections: int = 20
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600  # 1 hour
    pool_pre_ping: bool = True
    retry_attempts: int = 3
    retry_delay: float = 1.0
    health_check_interval: int = 60  # seconds
    connection_lifetime: int = 7200  # 2 hours


@dataclass
class PoolMetrics:
    """Connection pool metrics."""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    checked_out_connections: int = 0
    overflow_connections: int = 0
    failed_connections: int = 0
    total_checkouts: int = 0
    total_checkins: int = 0
    average_checkout_time: float = 0.0
    peak_connections: int = 0
    last_updated: datetime = None


class ConnectionPoolManager:
    """
    Advanced connection pool manager with monitoring and optimization.
    """
    
    def __init__(
        self,
        database_url: str,
        pool_config: Optional[PoolConfig] = None,
        enable_monitoring: bool = True
    ):
        self.database_url = database_url
        self.config = pool_config or PoolConfig()
        self.enable_monitoring = enable_monitoring
        
        # Connection pools
        self._async_pool: Optional[asyncpg.Pool] = None
        self._sync_pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None
        
        # Metrics and monitoring
        self.metrics = PoolMetrics()
        self._checkout_times: List[float] = []
        self._connection_registry: weakref.WeakSet = weakref.WeakSet()
        
        # Health monitoring
        self._health_check_task: Optional[asyncio.Task] = None
        self._monitoring_enabled = False
        
        # Thread safety
        self._lock = threading.Lock()
        
    async def initialize_async_pool(self) -> bool:
        """Initialize async connection pool."""
        try:
            logger.info("Initializing async connection pool")
            
            self._async_pool = await asyncpg.create_pool(
                self.database_url,
                min_size=self.config.min_connections,
                max_size=self.config.max_connections,
                max_queries=50000,
                max_inactive_connection_lifetime=self.config.connection_lifetime,
                command_timeout=60,
                server_settings={
                    'application_name': 'regulensai_async_pool',
                    'tcp_keepalives_idle': '600',
                    'tcp_keepalives_interval': '30',
                    'tcp_keepalives_count': '3'
                }
            )
            
            # Start health monitoring
            if self.enable_monitoring:
                await self._start_health_monitoring()
            
            logger.info(f"Async pool initialized with {self.config.min_connections}-{self.config.max_connections} connections")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize async pool: {e}")
            return False
    
    def initialize_sync_pool(self) -> bool:
        """Initialize sync connection pool."""
        try:
            logger.info("Initializing sync connection pool")
            
            # Parse database URL for psycopg2
            import urllib.parse
            parsed = urllib.parse.urlparse(self.database_url)
            
            self._sync_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=self.config.min_connections,
                maxconn=self.config.max_connections,
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path[1:],  # Remove leading slash
                user=parsed.username,
                password=parsed.password,
                application_name='regulensai_sync_pool'
            )
            
            logger.info(f"Sync pool initialized with {self.config.min_connections}-{self.config.max_connections} connections")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize sync pool: {e}")
            return False
    
    @asynccontextmanager
    async def get_async_connection(self):
        """Get async database connection from pool."""
        if not self._async_pool:
            raise RuntimeError("Async pool not initialized")
        
        start_time = time.time()
        connection = None
        
        try:
            # Get connection from pool
            connection = await asyncio.wait_for(
                self._async_pool.acquire(),
                timeout=self.config.pool_timeout
            )
            
            # Update metrics
            checkout_time = time.time() - start_time
            self._update_checkout_metrics(checkout_time)
            
            # Register connection for monitoring
            self._connection_registry.add(connection)
            
            yield connection
            
        except asyncio.TimeoutError:
            logger.error("Timeout acquiring connection from async pool")
            self.metrics.failed_connections += 1
            raise
            
        except Exception as e:
            logger.error(f"Error acquiring async connection: {e}")
            self.metrics.failed_connections += 1
            raise
            
        finally:
            if connection:
                try:
                    await self._async_pool.release(connection)
                    self.metrics.total_checkins += 1
                except Exception as e:
                    logger.error(f"Error releasing async connection: {e}")
    
    @asynccontextmanager
    async def get_sync_connection(self):
        """Get sync database connection from pool."""
        if not self._sync_pool:
            raise RuntimeError("Sync pool not initialized")
        
        start_time = time.time()
        connection = None
        
        try:
            # Get connection from pool
            connection = self._sync_pool.getconn()
            
            if connection is None:
                raise RuntimeError("Failed to get connection from sync pool")
            
            # Update metrics
            checkout_time = time.time() - start_time
            self._update_checkout_metrics(checkout_time)
            
            yield connection
            
        except Exception as e:
            logger.error(f"Error acquiring sync connection: {e}")
            self.metrics.failed_connections += 1
            raise
            
        finally:
            if connection:
                try:
                    self._sync_pool.putconn(connection)
                    self.metrics.total_checkins += 1
                except Exception as e:
                    logger.error(f"Error releasing sync connection: {e}")
    
    async def execute_async_query(
        self,
        query: str,
        params: Optional[tuple] = None,
        fetch_mode: str = "all"  # all, one, none
    ) -> Any:
        """Execute async query with connection pooling."""
        async with self.get_async_connection() as conn:
            try:
                if fetch_mode == "all":
                    return await conn.fetch(query, *(params or ()))
                elif fetch_mode == "one":
                    return await conn.fetchrow(query, *(params or ()))
                elif fetch_mode == "none":
                    return await conn.execute(query, *(params or ()))
                else:
                    raise ValueError(f"Invalid fetch_mode: {fetch_mode}")
                    
            except Exception as e:
                logger.error(f"Error executing async query: {e}")
                raise
    
    def execute_sync_query(
        self,
        query: str,
        params: Optional[tuple] = None,
        fetch_mode: str = "all"
    ) -> Any:
        """Execute sync query with connection pooling."""
        with self.get_sync_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    
                    if fetch_mode == "all":
                        return cursor.fetchall()
                    elif fetch_mode == "one":
                        return cursor.fetchone()
                    elif fetch_mode == "none":
                        conn.commit()
                        return cursor.rowcount
                    else:
                        raise ValueError(f"Invalid fetch_mode: {fetch_mode}")
                        
            except Exception as e:
                logger.error(f"Error executing sync query: {e}")
                conn.rollback()
                raise
    
    async def get_pool_status(self) -> Dict[str, Any]:
        """Get current pool status and metrics."""
        status = {
            "async_pool": None,
            "sync_pool": None,
            "metrics": self._get_current_metrics(),
            "config": {
                "min_connections": self.config.min_connections,
                "max_connections": self.config.max_connections,
                "max_overflow": self.config.max_overflow,
                "pool_timeout": self.config.pool_timeout
            }
        }
        
        # Async pool status
        if self._async_pool:
            status["async_pool"] = {
                "size": self._async_pool.get_size(),
                "min_size": self._async_pool.get_min_size(),
                "max_size": self._async_pool.get_max_size(),
                "idle_connections": self._async_pool.get_idle_size(),
                "is_closing": self._async_pool.is_closing()
            }
        
        # Sync pool status
        if self._sync_pool:
            with self._lock:
                status["sync_pool"] = {
                    "min_connections": self._sync_pool.minconn,
                    "max_connections": self._sync_pool.maxconn,
                    "current_connections": len(self._sync_pool._pool),
                    "available_connections": len([c for c in self._sync_pool._pool if not self._sync_pool._used.get(id(c), False)])
                }
        
        return status
    
    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on connection pools."""
        results = {
            "async_pool_healthy": False,
            "sync_pool_healthy": False,
            "overall_healthy": False
        }
        
        # Test async pool
        if self._async_pool:
            try:
                async with self.get_async_connection() as conn:
                    await conn.fetchval("SELECT 1")
                results["async_pool_healthy"] = True
            except Exception as e:
                logger.error(f"Async pool health check failed: {e}")
        
        # Test sync pool
        if self._sync_pool:
            try:
                with self.get_sync_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1")
                        cursor.fetchone()
                results["sync_pool_healthy"] = True
            except Exception as e:
                logger.error(f"Sync pool health check failed: {e}")
        
        results["overall_healthy"] = results["async_pool_healthy"] or results["sync_pool_healthy"]
        return results
    
    async def optimize_pool_size(self) -> Dict[str, Any]:
        """Optimize pool size based on usage patterns."""
        try:
            current_metrics = self._get_current_metrics()
            
            # Calculate optimal pool size based on metrics
            avg_active = current_metrics.active_connections
            peak_usage = current_metrics.peak_connections
            
            # Optimization recommendations
            recommendations = {
                "current_min": self.config.min_connections,
                "current_max": self.config.max_connections,
                "recommended_min": max(2, int(avg_active * 0.8)),
                "recommended_max": max(self.config.min_connections + 5, int(peak_usage * 1.2)),
                "optimization_needed": False,
                "reasons": []
            }
            
            # Check if optimization is needed
            if avg_active > self.config.max_connections * 0.8:
                recommendations["optimization_needed"] = True
                recommendations["reasons"].append("High average connection usage")
            
            if peak_usage > self.config.max_connections * 0.9:
                recommendations["optimization_needed"] = True
                recommendations["reasons"].append("Peak usage near maximum")
            
            if current_metrics.failed_connections > 0:
                recommendations["optimization_needed"] = True
                recommendations["reasons"].append("Connection failures detected")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error optimizing pool size: {e}")
            return {"error": str(e)}
    
    async def close_pools(self):
        """Close all connection pools."""
        logger.info("Closing connection pools")
        
        # Stop health monitoring
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Close async pool
        if self._async_pool:
            await self._async_pool.close()
            self._async_pool = None
        
        # Close sync pool
        if self._sync_pool:
            self._sync_pool.closeall()
            self._sync_pool = None
        
        logger.info("Connection pools closed")
    
    def _update_checkout_metrics(self, checkout_time: float):
        """Update connection checkout metrics."""
        with self._lock:
            self.metrics.total_checkouts += 1
            self._checkout_times.append(checkout_time)
            
            # Keep only last 1000 checkout times for average calculation
            if len(self._checkout_times) > 1000:
                self._checkout_times = self._checkout_times[-1000:]
            
            # Update average checkout time
            self.metrics.average_checkout_time = sum(self._checkout_times) / len(self._checkout_times)
    
    def _get_current_metrics(self) -> PoolMetrics:
        """Get current pool metrics."""
        with self._lock:
            # Update current connection counts
            if self._async_pool:
                self.metrics.total_connections = self._async_pool.get_size()
                self.metrics.idle_connections = self._async_pool.get_idle_size()
                self.metrics.active_connections = self.metrics.total_connections - self.metrics.idle_connections
            
            # Update peak connections
            if self.metrics.active_connections > self.metrics.peak_connections:
                self.metrics.peak_connections = self.metrics.active_connections
            
            self.metrics.last_updated = datetime.utcnow()
            
            return self.metrics
    
    async def _start_health_monitoring(self):
        """Start background health monitoring."""
        if self._monitoring_enabled:
            return
        
        self._monitoring_enabled = True
        self._health_check_task = asyncio.create_task(self._health_monitor_loop())
        logger.info("Health monitoring started")
    
    async def _health_monitor_loop(self):
        """Background health monitoring loop."""
        while self._monitoring_enabled:
            try:
                # Perform health check
                health_status = await self.health_check()
                
                if not health_status["overall_healthy"]:
                    logger.warning("Connection pool health check failed")
                
                # Update metrics
                self._get_current_metrics()
                
                # Sleep until next check
                await asyncio.sleep(self.config.health_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(self.config.health_check_interval)
    
    def get_connection_decorator(self, pool_type: str = "async"):
        """Decorator to automatically manage database connections."""
        def decorator(func: Callable) -> Callable:
            if pool_type == "async":
                async def async_wrapper(*args, **kwargs):
                    async with self.get_async_connection() as conn:
                        return await func(conn, *args, **kwargs)
                return async_wrapper
            else:
                def sync_wrapper(*args, **kwargs):
                    with self.get_sync_connection() as conn:
                        return func(conn, *args, **kwargs)
                return sync_wrapper
        
        return decorator


# Global connection pool manager
connection_pool_manager: Optional[ConnectionPoolManager] = None


async def initialize_connection_pools(
    database_url: str,
    pool_config: Optional[PoolConfig] = None
) -> bool:
    """Initialize global connection pool manager."""
    global connection_pool_manager
    
    try:
        connection_pool_manager = ConnectionPoolManager(database_url, pool_config)
        
        # Initialize both async and sync pools
        async_success = await connection_pool_manager.initialize_async_pool()
        sync_success = connection_pool_manager.initialize_sync_pool()
        
        if async_success or sync_success:
            logger.info("Connection pools initialized successfully")
            return True
        else:
            logger.error("Failed to initialize any connection pools")
            return False
            
    except Exception as e:
        logger.error(f"Error initializing connection pools: {e}")
        return False


def get_connection_pool_manager() -> Optional[ConnectionPoolManager]:
    """Get the global connection pool manager."""
    return connection_pool_manager


# Convenience decorators
def with_async_db_connection(func: Callable) -> Callable:
    """Decorator to provide async database connection."""
    if not connection_pool_manager:
        raise RuntimeError("Connection pool manager not initialized")
    
    return connection_pool_manager.get_connection_decorator("async")(func)


def with_sync_db_connection(func: Callable) -> Callable:
    """Decorator to provide sync database connection."""
    if not connection_pool_manager:
        raise RuntimeError("Connection pool manager not initialized")
    
    return connection_pool_manager.get_connection_decorator("sync")(func)
