"""
Regulens AI - Monitoring and Observability Framework
Enterprise-grade monitoring with metrics, tracing, and health checks.
"""

import asyncio
import time
import uuid
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import structlog

from core_infra.config import get_settings
from core_infra.database.connection import get_database
from core_infra.performance.optimization import performance_optimizer
from core_infra.exceptions import SystemException

# Initialize logging
logger = structlog.get_logger(__name__)
settings = get_settings()

class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class MetricType(Enum):
    """Metric type enumeration."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"

@dataclass
class HealthCheck:
    """Health check result."""
    service_name: str
    check_type: str
    status: HealthStatus
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    timestamp: datetime = None

@dataclass
class Metric:
    """Metric data structure."""
    name: str
    value: float
    metric_type: MetricType
    unit: str = "count"
    tags: Dict[str, str] = None
    timestamp: datetime = None

class SystemMonitor:
    """System resource monitoring."""
    
    def __init__(self):
        self.monitoring_interval = 30  # seconds
        self.alert_thresholds = {
            'cpu_percent': 80,
            'memory_percent': 85,
            'disk_percent': 90,
            'response_time_ms': 5000
        }
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_gb = memory.available / (1024**3)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_free_gb = disk.free / (1024**3)
            
            # Network metrics
            network = psutil.net_io_counters()
            
            # Process metrics
            process = psutil.Process()
            process_memory = process.memory_info()
            process_cpu = process.cpu_percent()
            
            return {
                'cpu': {
                    'percent': cpu_percent,
                    'count': cpu_count,
                    'process_percent': process_cpu
                },
                'memory': {
                    'percent': memory_percent,
                    'available_gb': round(memory_available_gb, 2),
                    'total_gb': round(memory.total / (1024**3), 2),
                    'process_mb': round(process_memory.rss / (1024**2), 2)
                },
                'disk': {
                    'percent': disk_percent,
                    'free_gb': round(disk_free_gb, 2),
                    'total_gb': round(disk.total / (1024**3), 2)
                },
                'network': {
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv,
                    'packets_sent': network.packets_sent,
                    'packets_recv': network.packets_recv
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"System metrics collection failed: {e}")
            return {'error': str(e)}
    
    async def check_system_health(self) -> HealthCheck:
        """Check overall system health."""
        try:
            metrics = await self.get_system_metrics()
            
            if 'error' in metrics:
                return HealthCheck(
                    service_name='system',
                    check_type='resource_monitoring',
                    status=HealthStatus.UNHEALTHY,
                    error_message=metrics['error'],
                    timestamp=datetime.utcnow()
                )
            
            # Determine health status based on thresholds
            status = HealthStatus.HEALTHY
            issues = []
            
            if metrics['cpu']['percent'] > self.alert_thresholds['cpu_percent']:
                status = HealthStatus.DEGRADED
                issues.append(f"High CPU usage: {metrics['cpu']['percent']}%")
            
            if metrics['memory']['percent'] > self.alert_thresholds['memory_percent']:
                status = HealthStatus.DEGRADED
                issues.append(f"High memory usage: {metrics['memory']['percent']}%")
            
            if metrics['disk']['percent'] > self.alert_thresholds['disk_percent']:
                status = HealthStatus.UNHEALTHY
                issues.append(f"High disk usage: {metrics['disk']['percent']}%")
            
            return HealthCheck(
                service_name='system',
                check_type='resource_monitoring',
                status=status,
                error_message='; '.join(issues) if issues else None,
                metadata=metrics,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"System health check failed: {e}")
            return HealthCheck(
                service_name='system',
                check_type='resource_monitoring',
                status=HealthStatus.UNHEALTHY,
                error_message=str(e),
                timestamp=datetime.utcnow()
            )

class ServiceHealthChecker:
    """Service-specific health checking."""
    
    def __init__(self):
        self.health_checks = {}
        self.check_interval = 60  # seconds
        
    async def register_health_check(self, service_name: str, check_func: Callable):
        """Register a health check function for a service."""
        self.health_checks[service_name] = check_func
        logger.info(f"Health check registered for service: {service_name}")
    
    async def check_service_health(self, service_name: str) -> HealthCheck:
        """Check health of a specific service."""
        try:
            if service_name not in self.health_checks:
                return HealthCheck(
                    service_name=service_name,
                    check_type='service_check',
                    status=HealthStatus.UNKNOWN,
                    error_message="No health check registered",
                    timestamp=datetime.utcnow()
                )
            
            start_time = time.time()
            check_func = self.health_checks[service_name]
            
            # Execute health check with timeout
            try:
                result = await asyncio.wait_for(check_func(), timeout=30)
                response_time_ms = (time.time() - start_time) * 1000
                
                if isinstance(result, HealthCheck):
                    result.response_time_ms = response_time_ms
                    return result
                else:
                    # Convert boolean or dict result to HealthCheck
                    if result is True or (isinstance(result, dict) and result.get('healthy', False)):
                        return HealthCheck(
                            service_name=service_name,
                            check_type='service_check',
                            status=HealthStatus.HEALTHY,
                            response_time_ms=response_time_ms,
                            metadata=result if isinstance(result, dict) else None,
                            timestamp=datetime.utcnow()
                        )
                    else:
                        return HealthCheck(
                            service_name=service_name,
                            check_type='service_check',
                            status=HealthStatus.UNHEALTHY,
                            response_time_ms=response_time_ms,
                            error_message=str(result) if result else "Health check failed",
                            timestamp=datetime.utcnow()
                        )
                        
            except asyncio.TimeoutError:
                return HealthCheck(
                    service_name=service_name,
                    check_type='service_check',
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=(time.time() - start_time) * 1000,
                    error_message="Health check timeout",
                    timestamp=datetime.utcnow()
                )
                
        except Exception as e:
            logger.error(f"Health check failed for {service_name}: {e}")
            return HealthCheck(
                service_name=service_name,
                check_type='service_check',
                status=HealthStatus.UNHEALTHY,
                error_message=str(e),
                timestamp=datetime.utcnow()
            )
    
    async def check_all_services(self) -> Dict[str, HealthCheck]:
        """Check health of all registered services."""
        results = {}
        
        for service_name in self.health_checks.keys():
            results[service_name] = await self.check_service_health(service_name)
        
        return results

class MetricsCollector:
    """Metrics collection and aggregation."""
    
    def __init__(self):
        self.metrics_buffer = []
        self.buffer_size = 1000
        self.flush_interval = 60  # seconds
        self.custom_metrics = {}
        
    async def initialize(self):
        """Initialize metrics collector."""
        try:
            # Start background metrics flushing
            asyncio.create_task(self._metrics_flush_loop())
            logger.info("Metrics collector initialized")
        except Exception as e:
            logger.error(f"Metrics collector initialization failed: {e}")
    
    async def record_metric(self, name: str, value: float, metric_type: MetricType = MetricType.GAUGE,
                          unit: str = "count", tags: Dict[str, str] = None):
        """Record a metric."""
        metric = Metric(
            name=name,
            value=value,
            metric_type=metric_type,
            unit=unit,
            tags=tags or {},
            timestamp=datetime.utcnow()
        )
        
        self.metrics_buffer.append(metric)
        
        # Update custom metrics for real-time access
        metric_key = f"{name}:{':'.join(f'{k}={v}' for k, v in (tags or {}).items())}"
        self.custom_metrics[metric_key] = metric
        
        # Flush if buffer is full
        if len(self.metrics_buffer) >= self.buffer_size:
            await self._flush_metrics()
    
    async def increment_counter(self, name: str, value: float = 1, tags: Dict[str, str] = None):
        """Increment a counter metric."""
        await self.record_metric(name, value, MetricType.COUNTER, "count", tags)
    
    async def set_gauge(self, name: str, value: float, unit: str = "count", tags: Dict[str, str] = None):
        """Set a gauge metric."""
        await self.record_metric(name, value, MetricType.GAUGE, unit, tags)
    
    async def record_timer(self, name: str, duration_ms: float, tags: Dict[str, str] = None):
        """Record a timer metric."""
        await self.record_metric(name, duration_ms, MetricType.TIMER, "ms", tags)
    
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
    
    async def get_metric_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get metric summary for the specified time period."""
        try:
            async with get_database() as db:
                start_time = datetime.utcnow() - timedelta(hours=hours)
                
                # Get metric counts by name
                metric_counts = await db.fetch(
                    """
                    SELECT 
                        metric_name,
                        COUNT(*) as count,
                        AVG(metric_value) as avg_value,
                        MIN(metric_value) as min_value,
                        MAX(metric_value) as max_value
                    FROM performance_metrics
                    WHERE timestamp >= $1
                    GROUP BY metric_name
                    ORDER BY count DESC
                    """,
                    start_time
                )
                
                return {
                    'time_period_hours': hours,
                    'metrics': [dict(row) for row in metric_counts],
                    'total_metrics': len(metric_counts),
                    'buffer_size': len(self.metrics_buffer)
                }
                
        except Exception as e:
            logger.error(f"Failed to get metric summary: {e}")
            return {'error': str(e)}

class ObservabilityManager:
    """Main observability manager coordinating all monitoring components."""
    
    def __init__(self):
        self.system_monitor = SystemMonitor()
        self.service_health_checker = ServiceHealthChecker()
        self.metrics_collector = MetricsCollector()
        self.monitoring_enabled = True
        
    async def initialize(self):
        """Initialize all monitoring components."""
        try:
            await self.metrics_collector.initialize()
            await self._register_default_health_checks()
            await self._start_monitoring_loops()
            logger.info("Observability manager initialized successfully")
        except Exception as e:
            logger.error(f"Observability manager initialization failed: {e}")
            raise SystemException(f"Monitoring initialization failed: {e}")
    
    async def _register_default_health_checks(self):
        """Register default health checks."""
        # Database health check
        async def database_health_check():
            try:
                async with get_database() as db:
                    await db.fetchval('SELECT 1')
                return True
            except Exception as e:
                return {'healthy': False, 'error': str(e)}
        
        # Cache health check
        async def cache_health_check():
            try:
                await performance_optimizer.cache.set('health_check', 'ok', 10)
                result = await performance_optimizer.cache.get('health_check')
                return result == 'ok'
            except Exception as e:
                return {'healthy': False, 'error': str(e)}
        
        await self.service_health_checker.register_health_check('database', database_health_check)
        await self.service_health_checker.register_health_check('cache', cache_health_check)
    
    async def _start_monitoring_loops(self):
        """Start background monitoring loops."""
        if self.monitoring_enabled:
            asyncio.create_task(self._system_monitoring_loop())
            asyncio.create_task(self._health_check_loop())
    
    async def _system_monitoring_loop(self):
        """Background system monitoring loop."""
        while self.monitoring_enabled:
            try:
                # Collect system metrics
                system_metrics = await self.system_monitor.get_system_metrics()
                
                if 'error' not in system_metrics:
                    # Record system metrics
                    await self.metrics_collector.set_gauge('system.cpu.percent', system_metrics['cpu']['percent'], '%')
                    await self.metrics_collector.set_gauge('system.memory.percent', system_metrics['memory']['percent'], '%')
                    await self.metrics_collector.set_gauge('system.disk.percent', system_metrics['disk']['percent'], '%')
                    await self.metrics_collector.set_gauge('system.memory.available_gb', system_metrics['memory']['available_gb'], 'GB')
                
                await asyncio.sleep(self.system_monitor.monitoring_interval)
                
            except Exception as e:
                logger.error(f"System monitoring loop error: {e}")
                await asyncio.sleep(30)
    
    async def _health_check_loop(self):
        """Background health check loop."""
        while self.monitoring_enabled:
            try:
                # Perform system health check
                system_health = await self.system_monitor.check_system_health()
                await self._store_health_check(system_health)
                
                # Perform service health checks
                service_health_results = await self.service_health_checker.check_all_services()
                for health_check in service_health_results.values():
                    await self._store_health_check(health_check)
                
                await asyncio.sleep(self.service_health_checker.check_interval)
                
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(30)
    
    async def _store_health_check(self, health_check: HealthCheck):
        """Store health check result in database."""
        try:
            async with get_database() as db:
                await db.execute(
                    """
                    INSERT INTO system_health_checks (
                        service_name, check_type, status, response_time_ms, 
                        error_message, metadata, checked_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    health_check.service_name,
                    health_check.check_type,
                    health_check.status.value,
                    health_check.response_time_ms,
                    health_check.error_message,
                    health_check.metadata,
                    health_check.timestamp or datetime.utcnow()
                )
        except Exception as e:
            logger.error(f"Failed to store health check: {e}")
    
    async def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        try:
            # Get recent health checks
            async with get_database() as db:
                recent_checks = await db.fetch(
                    """
                    SELECT DISTINCT ON (service_name, check_type) 
                        service_name, check_type, status, response_time_ms, 
                        error_message, checked_at
                    FROM system_health_checks
                    WHERE checked_at >= NOW() - INTERVAL '5 minutes'
                    ORDER BY service_name, check_type, checked_at DESC
                    """
                )
            
            # Determine overall status
            statuses = [check['status'] for check in recent_checks]
            
            if not statuses:
                overall_status = HealthStatus.UNKNOWN
            elif all(status == 'healthy' for status in statuses):
                overall_status = HealthStatus.HEALTHY
            elif any(status == 'unhealthy' for status in statuses):
                overall_status = HealthStatus.UNHEALTHY
            else:
                overall_status = HealthStatus.DEGRADED
            
            return {
                'overall_status': overall_status.value,
                'timestamp': datetime.utcnow().isoformat(),
                'services': [dict(check) for check in recent_checks],
                'summary': {
                    'total_services': len(recent_checks),
                    'healthy_services': sum(1 for s in statuses if s == 'healthy'),
                    'degraded_services': sum(1 for s in statuses if s == 'degraded'),
                    'unhealthy_services': sum(1 for s in statuses if s == 'unhealthy')
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get overall health: {e}")
            return {
                'overall_status': HealthStatus.UNKNOWN.value,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

# Global observability manager instance
observability_manager = ObservabilityManager()

# Convenience functions
async def record_metric(name: str, value: float, metric_type: MetricType = MetricType.GAUGE,
                       unit: str = "count", tags: Dict[str, str] = None):
    """Convenience function for recording metrics."""
    await observability_manager.metrics_collector.record_metric(name, value, metric_type, unit, tags)

async def increment_counter(name: str, value: float = 1, tags: Dict[str, str] = None):
    """Convenience function for incrementing counters."""
    await observability_manager.metrics_collector.increment_counter(name, value, tags)

async def set_gauge(name: str, value: float, unit: str = "count", tags: Dict[str, str] = None):
    """Convenience function for setting gauges."""
    await observability_manager.metrics_collector.set_gauge(name, value, unit, tags)

async def record_timer(name: str, duration_ms: float, tags: Dict[str, str] = None):
    """Convenience function for recording timers."""
    await observability_manager.metrics_collector.record_timer(name, duration_ms, tags)

async def get_system_health() -> Dict[str, Any]:
    """Convenience function for getting system health."""
    return await observability_manager.get_overall_health()

async def register_health_check(service_name: str, check_func: Callable):
    """Convenience function for registering health checks."""
    await observability_manager.service_health_checker.register_health_check(service_name, check_func)
